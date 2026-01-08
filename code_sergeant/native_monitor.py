"""Native macOS activity monitoring.

Uses AppKit and Quartz frameworks for direct system access.
Provides a self-contained activity monitoring solution.
"""
import logging
import subprocess
import tempfile
import os
from datetime import datetime
from typing import Optional

from .models import ActivityEvent

logger = logging.getLogger("code_sergeant.native_monitor")

# Import macOS frameworks
try:
    from AppKit import NSWorkspace
    from Quartz import (
        CGWindowListCopyWindowInfo,
        kCGWindowListOptionOnScreenOnly,
        kCGNullWindowID,
        kCGWindowOwnerName,
        kCGWindowName,
        kCGWindowLayer,
        CGEventSourceSecondsSinceLastEventType,
        kCGEventSourceStateHIDSystemState,
        kCGAnyInputEventType,
    )
    MACOS_AVAILABLE = True
    logger.info("macOS native frameworks loaded successfully")
except ImportError as e:
    MACOS_AVAILABLE = False
    logger.warning(f"macOS frameworks not available: {e}")


class NativeMonitor:
    """
    Native macOS activity monitoring.
    
    Uses direct macOS APIs (AppKit, Quartz) to monitor active
    applications and window titles without external dependencies.
    """
    
    # Apps that indicate productive work (for thinking detection)
    PRODUCTIVE_APPS = [
        "cursor", "vscode", "code", "xcode", "terminal", "iterm", 
        "sublime", "vim", "nvim", "emacs", "intellij", "pycharm",
        "webstorm", "android studio", "visual studio", "atom",
        "figma", "sketch", "photoshop", "illustrator",
        "notion", "obsidian", "bear", "typora",
    ]
    
    # Thinking threshold: idle time in productive app that suggests thinking
    THINKING_IDLE_MIN = 30  # seconds
    THINKING_IDLE_MAX = 180  # seconds
    
    # AFK threshold: user is considered away after this
    AFK_THRESHOLD = 300  # 5 minutes
    
    def __init__(self):
        """Initialize native monitor."""
        if not MACOS_AVAILABLE:
            logger.error("macOS frameworks not available - native monitoring disabled")
        
        self.last_window_title: Optional[str] = None
        self.last_activity_time: Optional[datetime] = None
        logger.info("NativeMonitor initialized")
    
    def get_frontmost_app(self) -> str:
        """
        Get the currently active (frontmost) application name.
        
        Returns:
            Application name or "Unknown" if unavailable
        """
        if not MACOS_AVAILABLE:
            return "Unknown"
        
        try:
            workspace = NSWorkspace.sharedWorkspace()
            app = workspace.frontmostApplication()
            if app:
                return app.localizedName() or "Unknown"
            return "Unknown"
        except Exception as e:
            logger.warning(f"Error getting frontmost app: {e}")
            return "Unknown"
    
    def get_active_window_title(self) -> str:
        """
        Get the title of the frontmost window.
        
        Uses Quartz to enumerate windows and find the active one.
        
        Returns:
            Window title or empty string if unavailable
        """
        if not MACOS_AVAILABLE:
            return ""
        
        try:
            frontmost_app = self.get_frontmost_app()
            
            # Get list of on-screen windows
            windows = CGWindowListCopyWindowInfo(
                kCGWindowListOptionOnScreenOnly, 
                kCGNullWindowID
            )
            
            if not windows:
                return ""
            
            # Find windows belonging to the frontmost app
            for window in windows:
                owner = window.get(kCGWindowOwnerName, "")
                if owner == frontmost_app:
                    # Skip windows at layer 0 (desktop) or very high layers (overlays)
                    layer = window.get(kCGWindowLayer, 0)
                    if layer == 0:
                        continue
                    
                    title = window.get(kCGWindowName, "")
                    if title:
                        return title
            
            return ""
        except Exception as e:
            logger.warning(f"Error getting window title: {e}")
            return ""
    
    def get_idle_seconds(self) -> float:
        """
        Get seconds since last user input (keyboard/mouse).
        
        Returns:
            Idle time in seconds
        """
        if not MACOS_AVAILABLE:
            return 0.0
        
        try:
            idle_time = CGEventSourceSecondsSinceLastEventType(
                kCGEventSourceStateHIDSystemState,
                kCGAnyInputEventType
            )
            return float(idle_time)
        except Exception as e:
            logger.warning(f"Error getting idle time: {e}")
            return 0.0
    
    def is_user_idle(self, threshold_seconds: float = None) -> bool:
        """
        Check if user is idle (AFK).
        
        Args:
            threshold_seconds: Idle threshold (default: AFK_THRESHOLD)
            
        Returns:
            True if idle time exceeds threshold
        """
        if threshold_seconds is None:
            threshold_seconds = self.AFK_THRESHOLD
        return self.get_idle_seconds() > threshold_seconds
    
    def is_productive_app(self, app_name: str) -> bool:
        """
        Check if app is considered productive (for thinking detection).
        
        Args:
            app_name: Application name
            
        Returns:
            True if app is in productive apps list
        """
        app_lower = app_name.lower()
        return any(pa in app_lower for pa in self.PRODUCTIVE_APPS)
    
    def detect_activity_change(self, current_title: str) -> bool:
        """
        Detect if activity has changed (indicates user input).
        
        Args:
            current_title: Current window title
            
        Returns:
            True if activity changed
        """
        changed = (
            self.last_window_title is not None and 
            self.last_window_title != current_title
        )
        if changed:
            self.last_activity_time = datetime.now()
        self.last_window_title = current_title
        return changed
    
    def get_current_activity(self) -> ActivityEvent:
        """
        Get current activity using native macOS APIs.
        
        This is the main method - returns an ActivityEvent compatible
        with the rest of the application.
        
        Returns:
            ActivityEvent with current activity
        """
        if not MACOS_AVAILABLE:
            return ActivityEvent(
                ts=datetime.now(),
                app="Unknown",
                title="macOS APIs not available",
                is_afk=False
            )
        
        try:
            # Get current app and window
            app = self.get_frontmost_app()
            title = self.get_active_window_title()
            
            # Get idle time
            idle_seconds = self.get_idle_seconds()
            
            # Determine AFK status
            is_afk = idle_seconds > self.AFK_THRESHOLD
            
            # Detect activity change
            activity_changed = self.detect_activity_change(title)
            
            # Determine if user is likely thinking
            # (idle in productive app but not AFK)
            is_thinking = False
            if (self.THINKING_IDLE_MIN <= idle_seconds <= self.THINKING_IDLE_MAX 
                and self.is_productive_app(app)):
                is_thinking = True
                logger.debug(f"Detected thinking state: idle {idle_seconds:.0f}s in {app}")
            
            # Calculate last input time
            last_input_time = self.last_activity_time
            if activity_changed:
                last_input_time = datetime.now()
            
            activity = ActivityEvent(
                ts=datetime.now(),
                app=app,
                title=title,
                url=None,  # Native APIs don't provide URL
                is_afk=is_afk,
                keyboard_active=activity_changed or not is_afk,
                mouse_active=activity_changed or not is_afk,
                last_input_time=last_input_time,
                idle_duration_seconds=idle_seconds,
                is_thinking=is_thinking
            )
            
            logger.debug(
                f"Current activity: {app} — {title[:50] if title else 'No title'} "
                f"(AFK: {is_afk}, thinking: {is_thinking}, idle: {idle_seconds:.0f}s)"
            )
            return activity
            
        except Exception as e:
            logger.error(f"Error getting current activity: {e}")
            return ActivityEvent(
                ts=datetime.now(),
                app="Unknown",
                title=f"Error: {str(e)[:50]}",
                is_afk=False
            )
    
    def capture_screen(self, display_id: int = 0) -> Optional[bytes]:
        """
        Capture screenshot as PNG bytes.
        
        Uses macOS screencapture command for reliability.
        
        Args:
            display_id: Display to capture (0 = main display)
            
        Returns:
            PNG image bytes or None on failure
        """
        try:
            # Create temp file for screenshot
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                temp_file = f.name
            
            # Use screencapture command
            # -x: no sound
            # -C: capture cursor
            # -D: specify display
            result = subprocess.run(
                ['screencapture', '-x', '-D', str(display_id + 1), temp_file],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode != 0:
                logger.warning(f"screencapture failed: {result.stderr.decode()}")
                return None
            
            # Read the image data
            with open(temp_file, 'rb') as f:
                image_data = f.read()
            
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass
            
            logger.debug(f"Captured screenshot: {len(image_data)} bytes")
            return image_data
            
        except subprocess.TimeoutExpired:
            logger.warning("Screenshot capture timed out")
            return None
        except Exception as e:
            logger.error(f"Error capturing screen: {e}")
            return None
    
    def is_available(self) -> bool:
        """
        Check if native monitoring is available.
        
        Returns:
            True if macOS frameworks are available
        """
        return MACOS_AVAILABLE


# Convenience function for checking availability
def is_native_monitoring_available() -> bool:
    """Check if native macOS monitoring is available."""
    return MACOS_AVAILABLE

