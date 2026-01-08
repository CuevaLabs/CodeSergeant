"""
Pytest configuration and shared fixtures for Code Sergeant tests.

This module provides common fixtures used across all test modules:
- Mock AI clients for isolated testing
- Sample data (activities, judgments, etc.)
- Controller instances with mocked dependencies
- Bridge server test clients
"""

import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from code_sergeant.models import (  # noqa: E402
    ActivityEvent,
    Judgment,
    PersonalityProfile,
    PomodoroState,
    SessionStats,
)

# =============================================================================
# Mock Classes
# =============================================================================


class MockAIClient:
    """Mock AI client for testing without actual API calls."""

    def __init__(self, default_response: Optional[Dict[str, Any]] = None):
        self.default_response = default_response or {
            "classification": "on_task",
            "confidence": 0.85,
            "reason": "Activity matches goal",
            "say": "Good work, soldier!",
            "action": "none",
        }
        self.call_count = 0
        self.last_prompt = None
        self.should_fail = False
        self.fail_message = "Mock API failure"

    def chat(self, messages: list, **kwargs) -> Dict[str, Any]:
        """Mock chat completion."""
        self.call_count += 1
        self.last_prompt = messages

        if self.should_fail:
            raise Exception(self.fail_message)

        return {"message": {"content": str(self.default_response)}}

    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Mock text generation."""
        self.call_count += 1
        self.last_prompt = prompt

        if self.should_fail:
            raise Exception(self.fail_message)

        return {"response": str(self.default_response)}

    def get_status(self) -> Dict[str, Any]:
        """Get mock client status."""
        return {
            "openai_available": True,
            "openai_model": "gpt-4o-mini",
            "ollama_available": True,
            "ollama_model": "llama3.2",
            "ollama_vision_model": "llava",
            "primary_backend": "openai",
        }

    def check_ollama_available(self):
        """Check if Ollama is available."""
        return (True, "Ollama is available")

    def set_failure_mode(self, should_fail: bool, message: str = "Mock API failure"):
        """Configure the mock to simulate failures."""
        self.should_fail = should_fail
        self.fail_message = message


class MockTTSService:
    """Mock TTS service for testing without audio."""

    def __init__(self):
        self.spoken_texts = []
        self.started = False
        self.stopped = False

    def speak(self, text: str):
        """Record spoken text."""
        self.spoken_texts.append(text)

    def start(self):
        """Start the mock TTS service."""
        self.started = True

    def stop(self):
        """Stop the mock TTS service."""
        self.stopped = True

    def clear_queue(self) -> int:
        """Clear the speak queue."""
        count = len(self.spoken_texts)
        self.spoken_texts.clear()
        return count

    def cancel_all(self) -> int:
        """Cancel all pending speech."""
        return self.clear_queue()

    def wait_for_completion(self, timeout: float = 10.0) -> bool:
        """Wait for TTS completion (always returns True in mock)."""
        return True


class MockNativeMonitor:
    """Mock native monitor for testing without macOS APIs."""

    def __init__(self):
        self.current_app = "Cursor"
        self.current_title = "main.py - CodeSergeant"
        self.idle_seconds = 0

    def get_frontmost_app(self) -> str:
        """Get current frontmost app."""
        return self.current_app

    def get_active_window_title(self) -> str:
        """Get current window title."""
        return self.current_title

    def get_idle_seconds(self) -> float:
        """Get idle time in seconds."""
        return self.idle_seconds

    def is_user_idle(self, threshold: int = 120) -> bool:
        """Check if user is idle."""
        return self.idle_seconds > threshold

    def get_current_activity(self) -> ActivityEvent:
        """Get current activity as ActivityEvent."""
        return ActivityEvent(
            ts=datetime.now(),
            app=self.current_app,
            title=self.current_title,
            is_afk=self.is_user_idle(),
        )

    def set_activity(self, app: str, title: str, idle_seconds: float = 0):
        """Set mock activity for testing."""
        self.current_app = app
        self.current_title = title
        self.idle_seconds = idle_seconds


# =============================================================================
# Fixtures - Sample Data
# =============================================================================


@pytest.fixture
def sample_activity():
    """Create a sample activity event."""
    return ActivityEvent(
        ts=datetime.now(),
        app="Cursor",
        title="main.py - CodeSergeant",
        url=None,
        is_afk=False,
    )


@pytest.fixture
def sample_activity_off_task():
    """Create a sample off-task activity event."""
    return ActivityEvent(
        ts=datetime.now(),
        app="Twitter",
        title="Home / X",
        url="https://twitter.com",
        is_afk=False,
    )


@pytest.fixture
def sample_activity_idle():
    """Create a sample idle activity event."""
    return ActivityEvent(
        ts=datetime.now(), app="", title="", is_afk=True, idle_duration_seconds=300
    )


@pytest.fixture
def sample_activity_thinking():
    """Create a sample thinking activity event."""
    return ActivityEvent(
        ts=datetime.now(),
        app="Cursor",
        title="main.py - CodeSergeant",
        is_afk=False,
        is_thinking=True,
        idle_duration_seconds=45,
    )


@pytest.fixture
def sample_judgment_on_task():
    """Create a sample on-task judgment."""
    return Judgment(
        classification="on_task",
        confidence=0.9,
        reason="User is coding in relevant project",
        say="Good work, soldier!",
        action="none",
    )


@pytest.fixture
def sample_judgment_off_task():
    """Create a sample off-task judgment."""
    return Judgment(
        classification="off_task",
        confidence=0.85,
        reason="Social media is not productive",
        say="Focus, soldier! Back to work!",
        action="warn",
    )


@pytest.fixture
def sample_session_stats():
    """Create sample session statistics."""
    return SessionStats(
        start_time=datetime.now(),
        focus_seconds=1200,
        idle_seconds=60,
        off_task_seconds=120,
        thinking_seconds=180,
        distractions_count=2,
        pomodoros_completed=1,
    )


@pytest.fixture
def sample_pomodoro_state():
    """Create sample pomodoro state."""
    return PomodoroState(
        current_state="work",
        time_remaining_seconds=1500,
        work_duration_minutes=25,
        short_break_minutes=5,
        pomodoros_completed=0,
    )


# =============================================================================
# Fixtures - Mock Services
# =============================================================================


@pytest.fixture
def mock_ai_client():
    """Create a mock AI client."""
    return MockAIClient()


@pytest.fixture
def mock_ai_client_failing():
    """Create a mock AI client that simulates failures."""
    client = MockAIClient()
    client.set_failure_mode(True, "Simulated API failure")
    return client


@pytest.fixture
def mock_tts_service():
    """Create a mock TTS service."""
    return MockTTSService()


@pytest.fixture
def mock_native_monitor():
    """Create a mock native monitor."""
    return MockNativeMonitor()


# =============================================================================
# Fixtures - Configuration
# =============================================================================


@pytest.fixture
def sample_config():
    """Create sample configuration dictionary."""
    return {
        "poll_interval_sec": 0.5,
        "judge_interval_sec": 10,
        "cooldown_seconds": 30,
        "reminder_intervals_sec": [300, 600, 900],
        "voice": {
            "record_seconds": 5,
            "sample_rate": 16000,
            "note_record_seconds": 120,
        },
        "openai": {"api_key": None, "model": "gpt-4o-mini"},
        "ollama": {"model": "llama3.2", "base_url": "http://localhost:11434"},
        "tts": {"provider": "pyttsx3", "rate": 150, "volume": 0.8},
        "personality": {
            "name": "sergeant",
            "wake_word_name": "sergeant",
            "description": "A strict drill sergeant",
            "tone": ["strict", "firm"],
        },
        "pomodoro": {
            "work_duration_minutes": 25,
            "short_break_minutes": 5,
            "long_break_minutes": 15,
            "pomodoros_until_long_break": 4,
        },
        "screen_monitoring": {"enabled": False, "use_local_vision": True},
        "motivation": {"enabled": False, "check_interval_minutes": 3},
    }


@pytest.fixture
def sample_personality():
    """Create sample personality profile."""
    return PersonalityProfile.get_predefined("sergeant")


# =============================================================================
# Fixtures - Bridge Server
# =============================================================================


@pytest.fixture
def bridge_client():
    """Create a test client for the bridge server."""
    # Import here to avoid circular imports
    from bridge.server import app

    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


# =============================================================================
# Fixtures - Controller (with mocked dependencies)
# =============================================================================


@pytest.fixture
def mock_controller_deps(
    mock_ai_client, mock_tts_service, mock_native_monitor, sample_config
):
    """Create mocked dependencies for AppController testing."""
    return {
        "ai_client": mock_ai_client,
        "tts_service": mock_tts_service,
        "native_monitor": mock_native_monitor,
        "config": sample_config,
    }


# =============================================================================
# Utility Functions
# =============================================================================


def create_activity_sequence(apps: list[tuple[str, str]], interval_seconds: int = 10):
    """
    Create a sequence of activity events.

    Args:
        apps: List of (app_name, window_title) tuples
        interval_seconds: Time between activities

    Returns:
        List of ActivityEvent objects
    """
    activities = []
    base_time = datetime.now()

    for i, (app, title) in enumerate(apps):
        from datetime import timedelta

        ts = base_time + timedelta(seconds=i * interval_seconds)
        activities.append(ActivityEvent(ts=ts, app=app, title=title))

    return activities


def assert_judgment_valid(judgment: Judgment):
    """Assert that a judgment has valid structure."""
    assert judgment is not None
    assert judgment.classification in [
        "on_task",
        "off_task",
        "idle",
        "unknown",
        "thinking",
    ]
    assert 0.0 <= judgment.confidence <= 1.0
    assert judgment.action in ["none", "warn", "yell"]
    assert isinstance(judgment.reason, str)
    assert isinstance(judgment.say, str)
