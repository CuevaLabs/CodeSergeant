"""Autonomous motivation and flow state detection.

Monitors user behavior patterns to detect when they need encouragement,
are in flow state (don't interrupt), or might be struggling.
"""
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("code_sergeant.motivation")


@dataclass
class MotivationState:
    """Current motivation/mental state."""

    state: str  # "flow", "productive", "struggling", "distracted", "fatigued"
    confidence: float
    suggestion: str
    timestamp: datetime

    def should_interrupt(self) -> bool:
        """Check if we should interrupt the user."""
        # Never interrupt flow state
        if self.state == "flow":
            return False
        # Don't interrupt productive state unless confidence is high
        if self.state == "productive" and self.confidence < 0.8:
            return False
        return True


class MotivationMonitor:
    """
    Monitors user behavior to detect motivation state and provide
    contextual encouragement.

    States:
    - "flow": Deep focus, don't interrupt
    - "productive": Working well, light encouragement OK
    - "struggling": Stuck or frustrated, needs help
    - "distracted": Restless, frequent switching
    - "fatigued": Been working long, needs break
    """

    # Detection thresholds
    FLOW_MIN_FOCUS_MINUTES = 10  # At least 10 min focused for flow
    FLOW_MAX_IDLE_SECONDS = 30  # Max idle in flow state
    FLOW_MAX_APP_SWITCHES = 2  # Max switches in 5 min for flow

    DISTRACTED_MIN_SWITCHES = 5  # Switches in 5 min = distracted
    FATIGUED_MIN_MINUTES = 45  # Working 45+ min = check for fatigue

    STRUGGLING_IDLE_THRESHOLD = 120  # 2 min idle in productive app

    def __init__(
        self,
        ai_client=None,
        personality_manager=None,
        tts_service=None,
        check_interval_minutes: int = 3,
    ):
        """
        Initialize motivation monitor.

        Args:
            ai_client: AIClient instance for state detection
            personality_manager: For getting appropriate phrases
            tts_service: For speaking encouragement
            check_interval_minutes: How often to check motivation
        """
        self.ai_client = ai_client
        self.personality_manager = personality_manager
        self.tts_service = tts_service
        self.check_interval = check_interval_minutes * 60  # Convert to seconds

        # State tracking
        self.current_state: Optional[MotivationState] = None
        self.last_check_time: Optional[float] = None
        self.session_start_time: Optional[float] = None

        # App switch tracking (last 5 minutes)
        self.app_switches: deque = deque(maxlen=100)
        self.recent_apps: deque = deque(maxlen=20)
        self.last_app: Optional[str] = None

        # Worker thread
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None

        # Callbacks
        self.on_state_change: Optional[Callable[[MotivationState], None]] = None

        logger.info(
            f"MotivationMonitor initialized (check every {check_interval_minutes} min)"
        )

    def start(self, goal: str):
        """
        Start motivation monitoring for a session.

        Args:
            goal: Session goal
        """
        self.goal = goal
        self.session_start_time = time.time()
        self.last_check_time = None
        self.app_switches.clear()
        self.recent_apps.clear()
        self.last_app = None
        self.current_state = None

        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._worker_thread.start()

        logger.info(f"Motivation monitoring started for goal: {goal[:50]}...")

    def stop(self):
        """Stop motivation monitoring."""
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
        logger.info("Motivation monitoring stopped")

    def record_app_change(self, app_name: str):
        """
        Record an app switch for distraction detection.

        Args:
            app_name: New app name
        """
        if app_name != self.last_app:
            self.app_switches.append(time.time())
            self.recent_apps.append(app_name)
            self.last_app = app_name

    def get_recent_app_switches(self, window_seconds: int = 300) -> int:
        """
        Get number of app switches in the last N seconds.

        Args:
            window_seconds: Time window (default 5 minutes)

        Returns:
            Number of switches
        """
        cutoff = time.time() - window_seconds
        return sum(1 for ts in self.app_switches if ts > cutoff)

    def _monitor_loop(self):
        """Background loop for periodic motivation checks."""
        logger.info("Motivation monitor loop started")

        # Wait a bit before first check
        time.sleep(60)  # Wait 1 minute before first check

        while not self._stop_event.is_set():
            try:
                self._check_motivation()
            except Exception as e:
                logger.error(f"Error in motivation check: {e}")

            # Wait for next check
            self._stop_event.wait(timeout=self.check_interval)

        logger.info("Motivation monitor loop ended")

    def _check_motivation(self):
        """Perform a motivation state check."""
        if not self.session_start_time:
            return

        self.last_check_time = time.time()

        # Gather metrics
        focus_minutes = int((time.time() - self.session_start_time) / 60)
        app_switches = self.get_recent_app_switches(300)  # Last 5 min
        recent_apps = list(self.recent_apps)[-5:] if self.recent_apps else []

        # Try AI detection if available
        if self.ai_client:
            try:
                # Get current idle time from native monitor
                # (This would need to be passed in or accessed via controller)
                idle_seconds = 0  # Default, would be updated by controller

                result = self.ai_client.detect_motivation_state(
                    goal=self.goal,
                    focus_minutes=focus_minutes,
                    idle_seconds=idle_seconds,
                    app_switches=app_switches,
                    recent_apps=recent_apps,
                )

                new_state = MotivationState(
                    state=result.get("state", "productive"),
                    confidence=result.get("confidence", 0.5),
                    suggestion=result.get("suggestion", ""),
                    timestamp=datetime.now(),
                )

            except Exception as e:
                logger.warning(f"AI motivation detection failed: {e}, using rules")
                new_state = self._detect_state_rules(focus_minutes, app_switches, 0)
        else:
            # Use rule-based detection
            new_state = self._detect_state_rules(focus_minutes, app_switches, 0)

        # Handle state change
        old_state = self.current_state
        self.current_state = new_state

        if old_state is None or old_state.state != new_state.state:
            logger.info(
                f"Motivation state changed: {old_state.state if old_state else 'None'} -> {new_state.state}"
            )

            if self.on_state_change:
                self.on_state_change(new_state)

        # Provide encouragement if appropriate
        self._provide_encouragement(new_state)

    def _detect_state_rules(
        self,
        focus_minutes: int,
        app_switches: int,
        idle_seconds: float,
    ) -> MotivationState:
        """
        Rule-based motivation state detection.

        Args:
            focus_minutes: Minutes in session
            app_switches: App switches in last 5 min
            idle_seconds: Current idle time

        Returns:
            MotivationState
        """
        # Check for flow state
        if (
            focus_minutes >= self.FLOW_MIN_FOCUS_MINUTES
            and app_switches <= self.FLOW_MAX_APP_SWITCHES
            and idle_seconds <= self.FLOW_MAX_IDLE_SECONDS
        ):
            return MotivationState(
                state="flow",
                confidence=0.8,
                suggestion="",  # Don't suggest anything in flow
                timestamp=datetime.now(),
            )

        # Check for distracted state
        if app_switches >= self.DISTRACTED_MIN_SWITCHES:
            return MotivationState(
                state="distracted",
                confidence=0.7,
                suggestion="Try focusing on one thing at a time.",
                timestamp=datetime.now(),
            )

        # Check for fatigue
        if focus_minutes >= self.FATIGUED_MIN_MINUTES:
            return MotivationState(
                state="fatigued",
                confidence=0.6,
                suggestion="You've been working a while. Consider a break.",
                timestamp=datetime.now(),
            )

        # Check for struggling
        if idle_seconds >= self.STRUGGLING_IDLE_THRESHOLD:
            return MotivationState(
                state="struggling",
                confidence=0.6,
                suggestion="Need help? Try breaking down the problem.",
                timestamp=datetime.now(),
            )

        # Default: productive
        return MotivationState(
            state="productive",
            confidence=0.5,
            suggestion="Keep up the good work!",
            timestamp=datetime.now(),
        )

    def _provide_encouragement(self, state: MotivationState):
        """
        Provide contextual encouragement based on state.

        Args:
            state: Current motivation state
        """
        # Don't interrupt flow
        if state.state == "flow":
            logger.debug("In flow state - not interrupting")
            return

        # Get appropriate phrase
        phrase = None

        if self.personality_manager:
            if state.state == "struggling":
                phrase = self.personality_manager.get_phrase("encouragement_stuck")
            elif state.state == "distracted":
                phrase = self.personality_manager.get_phrase("refocus_gentle")
            elif state.state == "fatigued":
                phrase = self.personality_manager.get_phrase("break_suggestion")
            elif state.state == "productive":
                # Only occasionally encourage productive state
                if state.confidence > 0.7:
                    phrase = self.personality_manager.get_phrase(
                        "encouragement_general"
                    )

        # Fallback to suggestion
        if not phrase and state.suggestion:
            phrase = state.suggestion

        # Speak if we have something to say
        if phrase and self.tts_service:
            logger.info(f"Motivation encouragement ({state.state}): {phrase[:50]}...")
            self.tts_service.speak(phrase)

    def handle_user_statement(self, statement: str) -> Optional[str]:
        """
        Handle user statements that indicate motivation issues.

        Looks for phrases like "I'm stuck", "can't focus", "overwhelmed", etc.

        Args:
            statement: User's spoken statement

        Returns:
            Response phrase if motivation issue detected, None otherwise
        """
        statement_lower = statement.lower()

        # Keywords indicating different states
        stuck_keywords = [
            "stuck",
            "can't figure",
            "don't know",
            "confused",
            "lost",
            "no idea",
        ]
        focus_keywords = [
            "can't focus",
            "distracted",
            "keep thinking",
            "mind wandering",
        ]
        overwhelmed_keywords = ["overwhelmed", "too much", "stressed", "anxious"]
        tired_keywords = ["tired", "exhausted", "need a break", "burned out"]
        unmotivated_keywords = ["unmotivated", "don't want to", "bored", "pointless"]

        # Check for motivation issues
        response = None

        if any(kw in statement_lower for kw in stuck_keywords):
            if self.personality_manager:
                response = self.personality_manager.get_phrase("encouragement_stuck")
            else:
                response = (
                    "Let's break this down. What's the smallest next step you can take?"
                )

        elif any(kw in statement_lower for kw in focus_keywords):
            if self.personality_manager:
                response = self.personality_manager.get_phrase("refocus_gentle")
            else:
                response = "Let's refocus. Take a deep breath and return to your task."

        elif any(kw in statement_lower for kw in overwhelmed_keywords):
            response = "Take a moment. Write down the three most important things, then tackle one at a time."

        elif any(kw in statement_lower for kw in tired_keywords):
            response = "You've been working hard. Take a 5-minute break, stretch, then come back refreshed."

        elif any(kw in statement_lower for kw in unmotivated_keywords):
            if self.personality_manager:
                response = self.personality_manager.get_phrase("encouragement_general")
            else:
                response = (
                    "Remember why you started. One small win can rebuild momentum."
                )

        if response:
            logger.info(f"Detected motivation issue in statement: {statement[:50]}...")

        return response

    def get_current_state(self) -> Optional[MotivationState]:
        """Get the current motivation state."""
        return self.current_state

    def force_check(self, idle_seconds: float = 0) -> MotivationState:
        """
        Force an immediate motivation check.

        Args:
            idle_seconds: Current idle time

        Returns:
            Current motivation state
        """
        if not self.session_start_time:
            return MotivationState(
                state="productive",
                confidence=0.5,
                suggestion="",
                timestamp=datetime.now(),
            )

        focus_minutes = int((time.time() - self.session_start_time) / 60)
        app_switches = self.get_recent_app_switches(300)

        state = self._detect_state_rules(focus_minutes, app_switches, idle_seconds)
        self.current_state = state
        return state
