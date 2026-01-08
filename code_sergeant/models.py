"""Data models for Code Sergeant."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Literal, Optional


@dataclass
class ActivityEvent:
    """Represents a single activity observation."""

    ts: datetime
    app: str
    title: str
    url: Optional[str] = None
    is_afk: bool = False
    # Enhanced fields for better activity detection
    keyboard_active: bool = True
    mouse_active: bool = True
    last_input_time: Optional[datetime] = None
    idle_duration_seconds: float = 0.0
    is_thinking: bool = False  # Inferred from idle + no input but productive context


@dataclass
class Judgment:
    """Represents a judgment about whether activity matches the goal."""

    classification: Literal["on_task", "off_task", "idle", "unknown", "thinking"]
    confidence: float
    reason: str
    say: str  # <= 15 words
    action: Literal["none", "warn", "yell"]


@dataclass
class VoiceNote:
    """A voice note saved by the user."""

    timestamp: datetime
    content: str
    transcription: str


@dataclass
class DistractionLog:
    """Log entry for user-reported distraction."""

    timestamp: datetime
    reason: str
    is_phone: bool = False


@dataclass
class SessionStats:
    """Statistics for a focus session."""

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    focus_seconds: int = 0
    idle_seconds: int = 0
    off_task_seconds: int = 0
    thinking_seconds: int = 0
    distractions_count: int = 0
    best_focus_streak_seconds: int = 0
    current_focus_streak_seconds: int = 0
    # Enhanced fields for voice notes and logging
    voice_notes: List[VoiceNote] = field(default_factory=list)
    distraction_logs: List[DistractionLog] = field(default_factory=list)
    phone_reports: List[datetime] = field(default_factory=list)
    annotations: List[str] = field(default_factory=list)
    pomodoros_completed: int = 0


@dataclass
class PersonalityProfile:
    """Personality profile for customizing Code Sergeant's behavior."""

    name: Literal["sergeant", "buddy", "advisor", "coach", "custom"]
    wake_word_name: str  # Name used in wake word (e.g., "sergeant", "buddy")
    description: str  # Freeform description for LLM interpretation
    tone: List[str] = field(
        default_factory=list
    )  # e.g., ["strict", "firm"] or ["friendly", "supportive"]

    @classmethod
    def get_predefined(cls, name: str) -> "PersonalityProfile":
        """Get a predefined personality profile."""
        profiles = {
            "sergeant": cls(
                name="sergeant",
                wake_word_name="sergeant",
                description=(
                    "A strict drill sergeant who keeps you focused with firm, "
                    "no-nonsense commands. Uses military-style motivation."
                ),
                tone=["strict", "firm", "commanding", "no-nonsense"],
            ),
            "buddy": cls(
                name="buddy",
                wake_word_name="buddy",
                description=(
                    "A friendly, supportive friend who encourages you gently. "
                    "Uses casual, warm language."
                ),
                tone=["friendly", "supportive", "casual", "warm", "encouraging"],
            ),
            "advisor": cls(
                name="advisor",
                wake_word_name="advisor",
                description=(
                    "A professional, helpful advisor who provides thoughtful guidance. "
                    "Uses clear, respectful language."
                ),
                tone=["professional", "helpful", "respectful", "thoughtful", "clear"],
            ),
            "coach": cls(
                name="coach",
                wake_word_name="coach",
                description=(
                    "A motivational coach who inspires you to achieve your goals. "
                    "Uses energetic, positive language."
                ),
                tone=[
                    "motivational",
                    "energetic",
                    "positive",
                    "inspiring",
                    "action-oriented",
                ],
            ),
        }
        return profiles.get(name, profiles["sergeant"])


@dataclass
class PomodoroState:
    """State of the pomodoro timer."""

    current_state: Literal["stopped", "work", "short_break", "long_break"] = "stopped"
    time_remaining_seconds: int = 0
    work_duration_minutes: int = 25
    short_break_minutes: int = 5
    long_break_minutes: int = 15
    pomodoros_completed: int = 0
    pomodoros_until_long_break: int = 4
    is_paused: bool = False

    def get_display_time(self) -> str:
        """Get formatted time for display (MM:SS)."""
        minutes = self.time_remaining_seconds // 60
        seconds = self.time_remaining_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def get_state_emoji(self) -> str:
        """Get emoji for current state."""
        if self.current_state == "work":
            return "🍅"
        elif self.current_state in ("short_break", "long_break"):
            return "☕"
        return ""
