"""PyObjC Dashboard Window for Code Sergeant.

A native macOS window for session management with modern dark theme
and smooth animations for appearing/disappearing.
"""
import logging
import threading
from typing import Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger("code_sergeant.dashboard")

# Import PyObjC frameworks
try:
    from AppKit import (
        NSWindow, NSApplication, NSScreen, NSView, NSTextField,
        NSButton, NSSlider, NSColor, NSFont, NSMakeRect,
        NSWindowStyleMaskTitled, NSWindowStyleMaskClosable,
        NSWindowStyleMaskMiniaturizable, NSBackingStoreBuffered,
        NSTextFieldCell, NSCenterTextAlignment, NSLeftTextAlignment,
        NSRoundedBezelStyle, NSBezelStyleRounded,
        NSViewWidthSizable, NSViewHeightSizable,
        NSFocusRingTypeNone, NSLineBreakByTruncatingTail,
        NSApp, NSStackView, NSUserInterfaceLayoutOrientationVertical,
        NSLayoutAttributeWidth, NSLayoutAttributeHeight,
        NSProgressIndicator, NSProgressIndicatorStyleBar,
        NSBox, NSBoxSeparator, NSImage,
    )
    from Foundation import NSObject, NSTimer, NSRunLoop, NSDefaultRunLoopMode
    from Quartz import (
        CATransaction, CABasicAnimation,
        kCAMediaTimingFunctionEaseInEaseOut,
    )
    PYOBJC_AVAILABLE = True
    logger.info("PyObjC frameworks loaded for dashboard")
except ImportError as e:
    PYOBJC_AVAILABLE = False
    logger.warning(f"PyObjC not available for dashboard: {e}")


@dataclass
class DashboardConfig:
    """Configuration for the dashboard window."""
    window_width: int = 420
    window_height: int = 480
    corner_radius: float = 12.0
    animation_duration: float = 0.3
    
    # Colors (dark theme)
    bg_color: tuple = (0.12, 0.12, 0.14, 1.0)  # Dark gray
    text_color: tuple = (0.95, 0.95, 0.97, 1.0)  # Near white
    accent_color: tuple = (0.4, 0.6, 1.0, 1.0)  # Blue accent
    secondary_text: tuple = (0.6, 0.6, 0.65, 1.0)  # Gray text
    input_bg: tuple = (0.18, 0.18, 0.20, 1.0)  # Slightly lighter
    button_bg: tuple = (0.25, 0.5, 0.95, 1.0)  # Blue button
    button_secondary: tuple = (0.25, 0.25, 0.28, 1.0)  # Gray button


class DashboardWindow:
    """
    Native macOS dashboard window for Code Sergeant.
    
    Provides a modern dark-themed UI for session management with
    smooth animations for showing/hiding.
    """
    
    def __init__(
        self,
        on_start_session: Optional[Callable[[str, int, int], None]] = None,
        on_end_session: Optional[Callable[[], None]] = None,
    ):
        """
        Initialize dashboard window.
        
        Args:
            on_start_session: Callback when session starts (goal, work_minutes, break_minutes)
            on_end_session: Callback when session ends
        """
        if not PYOBJC_AVAILABLE:
            logger.error("PyObjC not available - dashboard disabled")
            self.window = None
            return
        
        self.config = DashboardConfig()
        self.on_start_session = on_start_session
        self.on_end_session = on_end_session
        
        # State
        self.is_session_active = False
        self._original_frame = None
        
        # UI elements (stored for updates)
        self._goal_field: Optional[NSTextField] = None
        self._work_slider: Optional[NSSlider] = None
        self._break_slider: Optional[NSSlider] = None
        self._work_label: Optional[NSTextField] = None
        self._break_label: Optional[NSTextField] = None
        self._start_button: Optional[NSButton] = None
        self._end_button: Optional[NSButton] = None
        self._stats_label: Optional[NSTextField] = None
        self._status_label: Optional[NSTextField] = None
        
        # Create window
        self._create_window()
        logger.info("Dashboard window created")
    
    def _create_window(self):
        """Create the main dashboard window."""
        # Calculate center position
        screen = NSScreen.mainScreen()
        screen_frame = screen.frame()
        x = (screen_frame.size.width - self.config.window_width) / 2
        y = (screen_frame.size.height - self.config.window_height) / 2
        
        # Create window
        frame = NSMakeRect(x, y, self.config.window_width, self.config.window_height)
        style = (
            NSWindowStyleMaskTitled |
            NSWindowStyleMaskClosable |
            NSWindowStyleMaskMiniaturizable
        )
        
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            style,
            NSBackingStoreBuffered,
            False
        )
        
        self.window.setTitle_("Code Sergeant")
        self.window.setBackgroundColor_(self._color(self.config.bg_color))
        self.window.setTitlebarAppearsTransparent_(True)
        self.window.setMovableByWindowBackground_(True)
        
        # Store original frame for animations
        self._original_frame = frame
        
        # Create content
        self._create_content()
    
    def _color(self, rgba: tuple) -> NSColor:
        """Create NSColor from RGBA tuple."""
        return NSColor.colorWithRed_green_blue_alpha_(*rgba)
    
    def _create_label(
        self, 
        text: str, 
        size: float = 14, 
        bold: bool = False,
        color: tuple = None,
        alignment: int = NSLeftTextAlignment
    ) -> NSTextField:
        """Create a styled label."""
        label = NSTextField.alloc().init()
        label.setStringValue_(text)
        label.setBezeled_(False)
        label.setDrawsBackground_(False)
        label.setEditable_(False)
        label.setSelectable_(False)
        
        if bold:
            label.setFont_(NSFont.boldSystemFontOfSize_(size))
        else:
            label.setFont_(NSFont.systemFontOfSize_(size))
        
        label.setTextColor_(self._color(color or self.config.text_color))
        label.setAlignment_(alignment)
        
        return label
    
    def _create_text_field(self, placeholder: str = "") -> NSTextField:
        """Create a styled text input field."""
        field = NSTextField.alloc().init()
        field.setPlaceholderString_(placeholder)
        field.setBezeled_(True)
        field.setEditable_(True)  # Allow text input
        field.setSelectable_(True)  # Allow text selection
        field.setDrawsBackground_(True)
        field.setBackgroundColor_(self._color(self.config.input_bg))
        field.setTextColor_(self._color(self.config.text_color))
        field.setFont_(NSFont.systemFontOfSize_(14))
        field.setFocusRingType_(NSFocusRingTypeNone)
        
        return field
    
    def _create_button(
        self, 
        title: str, 
        action: str,
        primary: bool = True
    ) -> NSButton:
        """Create a styled button."""
        button = NSButton.alloc().init()
        button.setTitle_(title)
        button.setBezelStyle_(NSBezelStyleRounded)
        button.setFont_(NSFont.boldSystemFontOfSize_(14))
        
        # Note: Button colors are handled by the system in modern macOS
        # For custom colors, would need to use NSButtonCell or layer-backed views
        
        return button
    
    def _create_slider(
        self, 
        min_val: float, 
        max_val: float, 
        default: float
    ) -> NSSlider:
        """Create a styled slider."""
        slider = NSSlider.alloc().init()
        slider.setMinValue_(min_val)
        slider.setMaxValue_(max_val)
        slider.setFloatValue_(default)
        slider.setContinuous_(True)
        
        return slider
    
    def _create_content(self):
        """Create all dashboard content."""
        content_view = self.window.contentView()
        
        # Padding
        padding = 24
        y_offset = self.config.window_height - 60  # Start below title bar
        
        # === Title ===
        title = self._create_label("⚔️ Code Sergeant", size=22, bold=True)
        title.setFrame_(NSMakeRect(padding, y_offset, self.config.window_width - 2*padding, 30))
        title.setAlignment_(NSCenterTextAlignment)
        content_view.addSubview_(title)
        y_offset -= 50
        
        # === Goal Section ===
        goal_label = self._create_label("What's your focus goal?", size=13, color=self.config.secondary_text)
        goal_label.setFrame_(NSMakeRect(padding, y_offset, self.config.window_width - 2*padding, 20))
        content_view.addSubview_(goal_label)
        y_offset -= 40
        
        self._goal_field = self._create_text_field("Enter your goal for this session...")
        self._goal_field.setFrame_(NSMakeRect(padding, y_offset, self.config.window_width - 2*padding, 32))
        content_view.addSubview_(self._goal_field)
        y_offset -= 50
        
        # === Work Duration ===
        work_header = self._create_label("Work Duration", size=13, color=self.config.secondary_text)
        work_header.setFrame_(NSMakeRect(padding, y_offset, 150, 20))
        content_view.addSubview_(work_header)
        
        self._work_label = self._create_label("25 min", size=13, bold=True)
        self._work_label.setFrame_(NSMakeRect(self.config.window_width - padding - 60, y_offset, 60, 20))
        self._work_label.setAlignment_(NSCenterTextAlignment)
        content_view.addSubview_(self._work_label)
        y_offset -= 30
        
        self._work_slider = self._create_slider(15, 60, 25)
        self._work_slider.setFrame_(NSMakeRect(padding, y_offset, self.config.window_width - 2*padding, 24))
        self._work_slider.setTarget_(self)
        self._work_slider.setAction_(b"workSliderChanged:")
        content_view.addSubview_(self._work_slider)
        y_offset -= 40
        
        # === Break Duration ===
        break_header = self._create_label("Break Duration", size=13, color=self.config.secondary_text)
        break_header.setFrame_(NSMakeRect(padding, y_offset, 150, 20))
        content_view.addSubview_(break_header)
        
        self._break_label = self._create_label("5 min", size=13, bold=True)
        self._break_label.setFrame_(NSMakeRect(self.config.window_width - padding - 60, y_offset, 60, 20))
        self._break_label.setAlignment_(NSCenterTextAlignment)
        content_view.addSubview_(self._break_label)
        y_offset -= 30
        
        self._break_slider = self._create_slider(5, 15, 5)
        self._break_slider.setFrame_(NSMakeRect(padding, y_offset, self.config.window_width - 2*padding, 24))
        self._break_slider.setTarget_(self)
        self._break_slider.setAction_(b"breakSliderChanged:")
        content_view.addSubview_(self._break_slider)
        y_offset -= 50
        
        # === Separator ===
        separator = NSBox.alloc().init()
        separator.setBoxType_(NSBoxSeparator)
        separator.setFrame_(NSMakeRect(padding, y_offset, self.config.window_width - 2*padding, 1))
        content_view.addSubview_(separator)
        y_offset -= 30
        
        # === Status Label ===
        self._status_label = self._create_label("Ready to focus", size=14)
        self._status_label.setFrame_(NSMakeRect(padding, y_offset, self.config.window_width - 2*padding, 20))
        self._status_label.setAlignment_(NSCenterTextAlignment)
        content_view.addSubview_(self._status_label)
        y_offset -= 30
        
        # === Stats Label ===
        self._stats_label = self._create_label("", size=12, color=self.config.secondary_text)
        self._stats_label.setFrame_(NSMakeRect(padding, y_offset, self.config.window_width - 2*padding, 40))
        self._stats_label.setAlignment_(NSCenterTextAlignment)
        content_view.addSubview_(self._stats_label)
        y_offset -= 60
        
        # === Buttons ===
        button_width = (self.config.window_width - 3*padding) / 2
        
        self._start_button = self._create_button("Start Session", "startSession:", primary=True)
        self._start_button.setFrame_(NSMakeRect(padding, y_offset, button_width, 40))
        self._start_button.setTarget_(self)
        self._start_button.setAction_(b"startSession:")
        content_view.addSubview_(self._start_button)
        
        self._end_button = self._create_button("End Session", "endSession:", primary=False)
        self._end_button.setFrame_(NSMakeRect(padding * 2 + button_width, y_offset, button_width, 40))
        self._end_button.setTarget_(self)
        self._end_button.setAction_(b"endSession:")
        self._end_button.setEnabled_(False)
        content_view.addSubview_(self._end_button)
    
    # === Action Methods ===
    
    def workSliderChanged_(self, sender):
        """Handle work duration slider change."""
        value = int(sender.floatValue())
        if self._work_label:
            self._work_label.setStringValue_(f"{value} min")
    
    def breakSliderChanged_(self, sender):
        """Handle break duration slider change."""
        value = int(sender.floatValue())
        if self._break_label:
            self._break_label.setStringValue_(f"{value} min")
    
    def startSession_(self, sender):
        """Handle start session button click."""
        if not self._goal_field:
            return
        
        goal = self._goal_field.stringValue()
        if not goal or not goal.strip():
            # Flash the field or show error
            self._goal_field.setBackgroundColor_(
                self._color((0.5, 0.2, 0.2, 1.0))
            )
            # Reset after delay
            def reset_color():
                if self._goal_field:
                    self._goal_field.setBackgroundColor_(
                        self._color(self.config.input_bg)
                    )
            threading.Timer(0.5, reset_color).start()
            return
        
        work_minutes = int(self._work_slider.floatValue()) if self._work_slider else 25
        break_minutes = int(self._break_slider.floatValue()) if self._break_slider else 5
        
        # Update UI state
        self.is_session_active = True
        self._update_session_ui()
        
        # Callback
        if self.on_start_session:
            self.on_start_session(goal.strip(), work_minutes, break_minutes)
        
        logger.info(f"Session started: goal='{goal}', work={work_minutes}min, break={break_minutes}min")
    
    def endSession_(self, sender):
        """Handle end session button click."""
        self.is_session_active = False
        self._update_session_ui()
        
        if self.on_end_session:
            self.on_end_session()
        
        logger.info("Session ended from dashboard")
    
    def _update_session_ui(self):
        """Update UI based on session state."""
        if self.is_session_active:
            if self._start_button:
                self._start_button.setEnabled_(False)
            if self._end_button:
                self._end_button.setEnabled_(True)
            if self._goal_field:
                self._goal_field.setEditable_(False)
            if self._work_slider:
                self._work_slider.setEnabled_(False)
            if self._break_slider:
                self._break_slider.setEnabled_(False)
            if self._status_label:
                self._status_label.setStringValue_("🟢 Session Active")
        else:
            if self._start_button:
                self._start_button.setEnabled_(True)
            if self._end_button:
                self._end_button.setEnabled_(False)
            if self._goal_field:
                self._goal_field.setEditable_(True)
                self._goal_field.setStringValue_("")
            if self._work_slider:
                self._work_slider.setEnabled_(True)
            if self._break_slider:
                self._break_slider.setEnabled_(True)
            if self._status_label:
                self._status_label.setStringValue_("Ready to focus")
    
    def update_stats(self, focus_minutes: int, distractions: int, status: str = None):
        """
        Update displayed stats during session.
        
        Args:
            focus_minutes: Minutes of focus time
            distractions: Number of distractions
            status: Optional status string
        """
        if self._stats_label:
            self._stats_label.setStringValue_(
                f"Focus: {focus_minutes} min | Distractions: {distractions}"
            )
        if status and self._status_label:
            self._status_label.setStringValue_(status)
    
    # === Window Management ===
    
    def show(self, animate: bool = True):
        """
        Show the dashboard window.
        
        Args:
            animate: Whether to animate the appearance
        """
        if not self.window:
            return
        
        if animate:
            self._animate_unsuck()
        else:
            self.window.center()
            self.window.makeKeyAndOrderFront_(None)
            NSApp.activateIgnoringOtherApps_(True)
    
    def hide(self, animate: bool = True):
        """
        Hide the dashboard window.
        
        Args:
            animate: Whether to animate the disappearance
        """
        if not self.window:
            return
        
        if animate:
            self._animate_suck()
        else:
            self.window.orderOut_(None)
    
    def _animate_suck(self):
        """Animate window 'sucking' into menu bar."""
        if not self.window:
            return
        
        # Get target position (top-right, near menu bar)
        screen = NSScreen.mainScreen()
        screen_frame = screen.frame()
        target_x = screen_frame.size.width - 50
        target_y = screen_frame.size.height - 30
        
        # Store current frame for later
        self._original_frame = self.window.frame()
        
        # Animate to small size at menu bar position
        target_frame = NSMakeRect(target_x, target_y, 10, 10)
        
        self.window.setFrame_display_animate_(target_frame, True, True)
        
        # Hide after animation
        def hide_after():
            if self.window:
                self.window.orderOut_(None)
        threading.Timer(0.3, hide_after).start()
        
        logger.debug("Dashboard suck animation started")
    
    def _animate_unsuck(self):
        """Animate window 'unsucking' from menu bar to center."""
        if not self.window:
            return
        
        # Calculate center position
        screen = NSScreen.mainScreen()
        screen_frame = screen.frame()
        center_x = (screen_frame.size.width - self.config.window_width) / 2
        center_y = (screen_frame.size.height - self.config.window_height) / 2
        
        # Start from small size at menu bar
        start_x = screen_frame.size.width - 50
        start_y = screen_frame.size.height - 30
        start_frame = NSMakeRect(start_x, start_y, 10, 10)
        
        # Target frame (centered)
        target_frame = NSMakeRect(
            center_x, center_y,
            self.config.window_width, self.config.window_height
        )
        
        # Set start position (no animation)
        self.window.setFrame_display_(start_frame, False)
        self.window.makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)
        
        # Animate to center
        self.window.setFrame_display_animate_(target_frame, True, True)
        
        logger.debug("Dashboard unsuck animation started")
    
    def is_visible(self) -> bool:
        """Check if window is currently visible."""
        if not self.window:
            return False
        return self.window.isVisible()
    
    def set_goal(self, goal: str):
        """Set the goal text field value."""
        if self._goal_field:
            self._goal_field.setStringValue_(goal)
    
    def get_goal(self) -> str:
        """Get the current goal text."""
        if self._goal_field:
            return self._goal_field.stringValue()
        return ""


def create_dashboard(
    on_start: Optional[Callable[[str, int, int], None]] = None,
    on_end: Optional[Callable[[], None]] = None
) -> Optional[DashboardWindow]:
    """
    Factory function to create dashboard window.
    
    Args:
        on_start: Callback for session start (goal, work_min, break_min)
        on_end: Callback for session end
        
    Returns:
        DashboardWindow instance or None if PyObjC unavailable
    """
    if not PYOBJC_AVAILABLE:
        logger.warning("Cannot create dashboard - PyObjC not available")
        return None
    
    return DashboardWindow(on_start_session=on_start, on_end_session=on_end)

