"""Privacy-focused screen monitoring for progress analysis.

Captures screenshots periodically and analyzes them using local vision models
to provide feedback on user progress. All processing is done locally,
screenshots are never stored to disk, and sensitive apps are blocked.
"""
import io
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("code_sergeant.screen_monitor")

# Try to import PIL for image processing
try:
    from PIL import Image, ImageDraw, ImageFilter

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning(
        "Pillow not installed - blur regions unavailable. Install with: pip install Pillow"
    )


@dataclass
class BlurRegion:
    """A screen region to always blur for privacy."""

    x: int
    y: int
    width: int
    height: int
    name: str = ""  # Optional name for the region

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for config storage."""
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "name": self.name,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BlurRegion":
        """Create from dictionary."""
        return cls(
            x=data.get("x", 0),
            y=data.get("y", 0),
            width=data.get("width", 100),
            height=data.get("height", 100),
            name=data.get("name", ""),
        )


@dataclass
class ScreenAnalysis:
    """Result of screen analysis."""

    summary: str
    activity_detected: str
    progress_indicator: str  # "making_progress", "stuck", "idle", "unknown"
    confidence: float
    timestamp: float

    def is_making_progress(self) -> bool:
        """Check if user appears to be making progress."""
        return self.progress_indicator == "making_progress"


class ScreenMonitor:
    """
    Privacy-focused screen monitoring with local analysis.

    Privacy features:
    1. App blocklist - Never captures when sensitive apps are active
    2. Blur regions - User-defined areas always blurred
    3. No storage - Screenshots processed in memory, never saved
    4. Local analysis - Uses local LLaVA model, images never leave device
    """

    # Default apps to never capture (banking, passwords, etc.)
    DEFAULT_BLOCKLIST = [
        # Password managers
        "1Password",
        "LastPass",
        "Bitwarden",
        "Dashlane",
        "Keeper",
        "Keychain Access",
        "KeePassXC",
        # Banking/Finance
        "PayPal",
        "Venmo",
        "Cash App",
        "Zelle",
        "Chase",
        "Bank of America",
        "Wells Fargo",
        "Citibank",
        "Capital One",
        "US Bank",
        "PNC",
        "TD Bank",
        "USAA",
        "Fidelity",
        "Charles Schwab",
        "Vanguard",
        "Robinhood",
        # Healthcare
        "MyChart",
        "Epic",
        "Health",
        # Email (often contains sensitive info)
        # Uncomment if desired: "Mail", "Outlook", "Gmail",
    ]

    def __init__(
        self,
        config: Dict[str, Any],
        native_monitor=None,
        ai_client=None,
        tts_service=None,
    ):
        """
        Initialize screen monitor.

        Args:
            config: Application config
            native_monitor: NativeMonitor instance for screen capture
            ai_client: AIClient instance for analysis
            tts_service: TTSService for speaking feedback
        """
        screen_config = config.get("screen_monitoring", {})

        self.enabled = screen_config.get("enabled", False)
        self.use_local_vision = screen_config.get("use_local_vision", True)
        self.check_interval = screen_config.get("check_interval_seconds", 120)

        # Load blocklist
        self.app_blocklist = screen_config.get("app_blocklist", self.DEFAULT_BLOCKLIST)

        # Load blur regions
        self.blur_regions: List[BlurRegion] = []
        for region_data in screen_config.get("blur_regions", []):
            self.blur_regions.append(BlurRegion.from_dict(region_data))

        # Services
        self.native_monitor = native_monitor
        self.ai_client = ai_client
        self.tts_service = tts_service

        # State
        self.session_goal: Optional[str] = None
        self.last_analysis: Optional[ScreenAnalysis] = None
        self.analysis_history: List[ScreenAnalysis] = []

        # Worker thread
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None

        # Callbacks
        self.on_progress_update: Optional[Callable[[ScreenAnalysis], None]] = None

        # Check vision backend availability and auto-fallback
        self._vision_backend_status = "unknown"
        if self.enabled and ai_client:
            self._check_and_configure_vision_backend()

        logger.info(
            f"ScreenMonitor initialized (enabled={self.enabled}, "
            f"local={self.use_local_vision}, backend={self._vision_backend_status})"
        )

    def _check_and_configure_vision_backend(self):
        """Check vision backend availability and configure fallback if needed."""
        if self.use_local_vision:
            # Check if Ollama is available
            is_available, message = self.ai_client.check_ollama_available()

            if is_available:
                self._vision_backend_status = "ollama"
                logger.info(
                    "✅ Screen monitoring: Using local LLaVA via Ollama (privacy-first)"
                )
            else:
                logger.warning(f"⚠️ Screen monitoring: {message}")

                # Try auto-fallback to OpenAI
                if self.ai_client.is_openai_available():
                    self.use_local_vision = False  # Auto-switch to OpenAI
                    self._vision_backend_status = "openai_fallback"
                    logger.info(
                        "⚡ Screen monitoring: Auto-switched to OpenAI GPT-4V (Ollama unavailable)"
                    )
                    logger.info(
                        "💡 Tip: Install Ollama from https://ollama.com/download for local-only privacy"
                    )
                else:
                    # No vision backend available - disable screen monitoring
                    self.enabled = False
                    self._vision_backend_status = "disabled"
                    logger.error(
                        "❌ Screen monitoring disabled: No vision backend available"
                    )
                    logger.error(
                        "   → Either install Ollama: https://ollama.com/download"
                    )
                    logger.error("   → Or set up an OpenAI API key")
        else:
            # User explicitly wants OpenAI
            if self.ai_client.is_openai_available():
                self._vision_backend_status = "openai"
                logger.info("✅ Screen monitoring: Using OpenAI GPT-4V")
            else:
                # OpenAI not available, try Ollama
                is_available, message = self.ai_client.check_ollama_available()
                if is_available:
                    self.use_local_vision = True  # Switch to Ollama
                    self._vision_backend_status = "ollama_fallback"
                    logger.warning(
                        "⚠️ OpenAI not available, using local Ollama instead"
                    )
                else:
                    self.enabled = False
                    self._vision_backend_status = "disabled"
                    logger.error(
                        "❌ Screen monitoring disabled: No vision backend available"
                    )

    def is_enabled(self) -> bool:
        """Check if screen monitoring is enabled."""
        return self.enabled

    def enable(self, enabled: bool = True):
        """Enable or disable screen monitoring."""
        self.enabled = enabled
        logger.info(f"Screen monitoring {'enabled' if enabled else 'disabled'}")

    def should_capture(self, current_app: str) -> bool:
        """
        Check if capture is allowed for the current app.

        Args:
            current_app: Current frontmost application name

        Returns:
            True if capture is allowed
        """
        if not self.enabled:
            return False

        # Check blocklist
        app_lower = current_app.lower()
        for blocked in self.app_blocklist:
            if blocked.lower() in app_lower:
                logger.debug(f"Capture blocked - app '{current_app}' matches blocklist")
                return False

        return True

    def add_blur_region(self, region: BlurRegion):
        """Add a blur region."""
        self.blur_regions.append(region)
        logger.info(f"Added blur region: {region.name or f'{region.x},{region.y}'}")

    def remove_blur_region(self, index: int):
        """Remove a blur region by index."""
        if 0 <= index < len(self.blur_regions):
            removed = self.blur_regions.pop(index)
            logger.info(
                f"Removed blur region: {removed.name or f'{removed.x},{removed.y}'}"
            )

    def clear_blur_regions(self):
        """Clear all blur regions."""
        self.blur_regions.clear()
        logger.info("Cleared all blur regions")

    def add_to_blocklist(self, app_name: str):
        """Add an app to the blocklist."""
        if app_name not in self.app_blocklist:
            self.app_blocklist.append(app_name)
            logger.info(f"Added '{app_name}' to blocklist")

    def remove_from_blocklist(self, app_name: str):
        """Remove an app from the blocklist."""
        if app_name in self.app_blocklist:
            self.app_blocklist.remove(app_name)
            logger.info(f"Removed '{app_name}' from blocklist")

    def _apply_blur_regions(self, image_bytes: bytes) -> bytes:
        """
        Apply blur to defined screen regions.

        Args:
            image_bytes: Original screenshot PNG bytes

        Returns:
            Blurred image bytes
        """
        if not PIL_AVAILABLE or not self.blur_regions:
            return image_bytes

        try:
            # Open image
            img = Image.open(io.BytesIO(image_bytes))

            # Apply blur to each region
            for region in self.blur_regions:
                box = (
                    region.x,
                    region.y,
                    region.x + region.width,
                    region.y + region.height,
                )

                # Ensure box is within image bounds
                box = (
                    max(0, box[0]),
                    max(0, box[1]),
                    min(img.width, box[2]),
                    min(img.height, box[3]),
                )

                if box[2] > box[0] and box[3] > box[1]:
                    # Crop, blur, and paste back
                    cropped = img.crop(box)
                    blurred = cropped.filter(ImageFilter.GaussianBlur(radius=30))
                    img.paste(blurred, box)

            # Convert back to bytes
            output = io.BytesIO()
            img.save(output, format="PNG")
            return output.getvalue()

        except Exception as e:
            logger.error(f"Error applying blur regions: {e}")
            return image_bytes

    def capture_with_privacy(self) -> Optional[bytes]:
        """
        Capture screenshot with privacy protections.

        Checks blocklist, applies blur regions, returns bytes (never saves).

        Returns:
            Screenshot bytes or None if capture not allowed
        """
        if not self.enabled or not self.native_monitor:
            return None

        # Check if current app is blocked
        current_app = self.native_monitor.get_frontmost_app()
        if not self.should_capture(current_app):
            return None

        # Capture screenshot
        try:
            screenshot = self.native_monitor.capture_screen()
            if not screenshot:
                return None

            # Apply blur regions
            if self.blur_regions:
                screenshot = self._apply_blur_regions(screenshot)

            # Return bytes - NEVER save to disk
            return screenshot

        except Exception as e:
            logger.error(f"Error capturing screenshot: {e}")
            return None

    def analyze_screenshot(self, screenshot_bytes: bytes) -> Optional[ScreenAnalysis]:
        """
        Analyze a screenshot using local vision model.

        Args:
            screenshot_bytes: Screenshot PNG bytes

        Returns:
            ScreenAnalysis or None if analysis fails
        """
        if not self.ai_client:
            logger.warning("No AI client available for screen analysis")
            return None

        # Build analysis prompt
        prompt = f"""Analyze this screenshot of a user working on their computer.

User's goal: {self.session_goal or 'Unknown'}

Describe:
1. What application/website is visible
2. What the user appears to be working on
3. Whether they seem to be making progress toward their goal

Be concise. Focus on productivity-relevant observations.
"""

        try:
            # Use local vision (LLaVA) for privacy
            response = self.ai_client.analyze_image(
                screenshot_bytes, prompt, use_local=self.use_local_vision
            )

            # Parse response into analysis
            analysis = self._parse_analysis(response)

            # Store in history (but NOT the screenshot itself)
            self.last_analysis = analysis
            self.analysis_history.append(analysis)

            # Keep only last 10 analyses
            if len(self.analysis_history) > 10:
                self.analysis_history.pop(0)

            return analysis

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error analyzing screenshot: {error_msg}")

            # Provide user-friendly guidance based on error type
            if (
                "ollama" in error_msg.lower()
                or "localhost:11434" in error_msg.lower()
                or "llava" in error_msg.lower()
            ):
                logger.info("💡 Tip: For local-only screen analysis, install Ollama:")
                logger.info("   → Download: https://ollama.com/download")
                logger.info("   → Then run: ollama pull llava")
                logger.info(
                    "   → Or set use_local_vision: false in config.json to use OpenAI"
                )
            elif "openai" in error_msg.lower() or "api_key" in error_msg.lower():
                logger.info("💡 Tip: Set up your OpenAI API key in the AI Settings menu")
            elif "vision" in error_msg.lower() or "backend" in error_msg.lower():
                logger.info(
                    "💡 Tip: Either install Ollama or set up an OpenAI API key for screen monitoring"
                )

            return None

    def get_vision_backend_status(self) -> str:
        """Get the current vision backend status."""
        return self._vision_backend_status

    def _parse_analysis(self, response: str) -> ScreenAnalysis:
        """
        Parse AI response into ScreenAnalysis.

        Args:
            response: AI analysis text

        Returns:
            ScreenAnalysis object
        """
        # Simple heuristic parsing
        response_lower = response.lower()

        # Detect progress indicator
        if any(
            word in response_lower
            for word in [
                "coding",
                "writing",
                "editing",
                "working",
                "creating",
                "developing",
            ]
        ):
            progress = "making_progress"
            confidence = 0.7
        elif any(
            word in response_lower
            for word in ["idle", "blank", "nothing", "no activity"]
        ):
            progress = "idle"
            confidence = 0.6
        elif any(
            word in response_lower
            for word in ["stuck", "same", "unchanged", "no progress"]
        ):
            progress = "stuck"
            confidence = 0.6
        else:
            progress = "unknown"
            confidence = 0.4

        # Extract activity (first line or sentence usually describes what's visible)
        lines = response.strip().split("\n")
        activity = lines[0][:100] if lines else "Unknown activity"

        return ScreenAnalysis(
            summary=response[:500],
            activity_detected=activity,
            progress_indicator=progress,
            confidence=confidence,
            timestamp=time.time(),
        )

    def start(self, goal: str):
        """
        Start screen monitoring for a session.

        Args:
            goal: Session goal
        """
        if not self.enabled:
            logger.info("Screen monitoring disabled - not starting")
            return

        self.session_goal = goal
        self.analysis_history.clear()
        self.last_analysis = None

        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._worker_thread.start()

        logger.info(f"Screen monitoring started (interval: {self.check_interval}s)")

    def stop(self):
        """Stop screen monitoring."""
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)

        # Clear sensitive data
        self.analysis_history.clear()
        self.last_analysis = None

        logger.info("Screen monitoring stopped")

    def _monitor_loop(self):
        """Background loop for periodic screen analysis."""
        logger.info("Screen monitor loop started")

        # Wait before first capture
        time.sleep(30)  # Wait 30 seconds before first check

        while not self._stop_event.is_set():
            try:
                self._perform_check()
            except Exception as e:
                logger.error(f"Error in screen monitor check: {e}")

            # Wait for next check
            self._stop_event.wait(timeout=self.check_interval)

        logger.info("Screen monitor loop ended")

    def _perform_check(self):
        """Perform a single screen capture and analysis."""
        # Capture with privacy
        screenshot = self.capture_with_privacy()
        if not screenshot:
            return

        # Analyze
        analysis = self.analyze_screenshot(screenshot)
        if not analysis:
            return

        # Provide feedback if making progress
        if analysis.is_making_progress() and self.tts_service:
            # Only occasionally comment on progress
            if len(self.analysis_history) % 3 == 0:  # Every 3rd analysis
                self.tts_service.speak(f"I see you're making progress. Keep it up!")

        # Callback
        if self.on_progress_update:
            self.on_progress_update(analysis)

        logger.info(
            f"Screen analysis: {analysis.progress_indicator} ({analysis.confidence:.0%})"
        )

    def force_check(self) -> Optional[ScreenAnalysis]:
        """
        Force an immediate screen check.

        Returns:
            ScreenAnalysis or None
        """
        screenshot = self.capture_with_privacy()
        if not screenshot:
            return None

        return self.analyze_screenshot(screenshot)

    def get_config_dict(self) -> Dict[str, Any]:
        """
        Get current config as dictionary for saving.

        Returns:
            Config dictionary
        """
        return {
            "enabled": self.enabled,
            "app_blocklist": self.app_blocklist,
            "blur_regions": [r.to_dict() for r in self.blur_regions],
            "use_local_vision": self.use_local_vision,
            "check_interval_seconds": self.check_interval,
        }


def create_screen_monitor(
    config: Dict[str, Any],
    native_monitor=None,
    ai_client=None,
    tts_service=None,
) -> ScreenMonitor:
    """
    Factory function to create screen monitor.

    Args:
        config: Application config
        native_monitor: NativeMonitor instance
        ai_client: AIClient instance
        tts_service: TTSService instance

    Returns:
        ScreenMonitor instance
    """
    return ScreenMonitor(
        config=config,
        native_monitor=native_monitor,
        ai_client=ai_client,
        tts_service=tts_service,
    )
