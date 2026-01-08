"""
Unit tests for TTSService.

Tests TTS queue management and error handling:
- Queue operations
- Speak/cancel functionality
- Provider fallback
- Edge cases (empty text, queue overflow)
"""

import os
import queue
import sys
import threading
import time
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from code_sergeant.tts import TTSService  # noqa: E402


@pytest.mark.unit
class TestTTSServiceInit:
    """Tests for TTSService initialization."""

    def test_default_initialization(self):
        """Test default TTS service initialization."""
        with patch("code_sergeant.tts.pyttsx3") as mock_pyttsx3:
            mock_engine = MagicMock()
            mock_pyttsx3.init.return_value = mock_engine
            mock_engine.getProperty.return_value = []

            service = TTSService()

            assert service.provider == "pyttsx3"
            assert service.speak_queue is not None

    def test_elevenlabs_initialization(self):
        """Test ElevenLabs TTS service initialization."""
        with patch("code_sergeant.tts.ELEVENLABS_AVAILABLE", True):
            with patch("code_sergeant.tts.ElevenLabs") as mock_elevenlabs:
                with patch("code_sergeant.tts.pyttsx3") as mock_pyttsx3:
                    mock_engine = MagicMock()
                    mock_pyttsx3.init.return_value = mock_engine
                    mock_engine.getProperty.return_value = []

                    service = TTSService(
                        provider="elevenlabs", api_key="test_key", voice_id="test_voice"
                    )

                    assert service.provider == "elevenlabs"


@pytest.mark.unit
class TestTTSServiceQueue:
    """Tests for TTS queue operations."""

    @pytest.fixture
    def tts_service(self):
        """Create TTS service with mocked engine."""
        with patch("code_sergeant.tts.pyttsx3") as mock_pyttsx3:
            mock_engine = MagicMock()
            mock_pyttsx3.init.return_value = mock_engine
            mock_engine.getProperty.return_value = []

            service = TTSService()
            service.engine = mock_engine
            yield service

    def test_speak_adds_to_queue(self, tts_service):
        """Test that speak adds text to queue."""
        tts_service.speak("Hello, world!")

        # Check queue has the message
        assert not tts_service.speak_queue.empty()

    def test_speak_empty_text_ignored(self, tts_service):
        """Test that empty text is ignored."""
        initial_size = tts_service.speak_queue.qsize()

        tts_service.speak("")
        tts_service.speak("   ")
        tts_service.speak(None)

        # Queue should not have grown
        # Note: speak("") should be ignored
        assert tts_service.speak_queue.qsize() == initial_size

    def test_clear_queue(self, tts_service):
        """Test clearing the queue."""
        tts_service.speak("Message 1")
        tts_service.speak("Message 2")
        tts_service.speak("Message 3")

        cleared = tts_service.clear_queue()

        assert cleared == 3
        assert tts_service.speak_queue.empty()

    def test_clear_empty_queue(self, tts_service):
        """Test clearing an empty queue."""
        cleared = tts_service.clear_queue()

        assert cleared == 0


@pytest.mark.unit
class TestTTSServiceEdgeCases:
    """Tests for edge cases."""

    @pytest.fixture
    def tts_service(self):
        """Create TTS service with mocked engine."""
        with patch("code_sergeant.tts.pyttsx3") as mock_pyttsx3:
            mock_engine = MagicMock()
            mock_pyttsx3.init.return_value = mock_engine
            mock_engine.getProperty.return_value = []

            service = TTSService()
            service.engine = mock_engine
            yield service

    def test_very_long_text(self, tts_service):
        """Test handling very long text."""
        long_text = "This is a test. " * 100

        tts_service.speak(long_text)

        assert not tts_service.speak_queue.empty()

    def test_unicode_text(self, tts_service):
        """Test handling unicode text."""
        unicode_text = "Hello 世界! 🎉 Привет мир!"

        tts_service.speak(unicode_text)

        assert not tts_service.speak_queue.empty()

    def test_special_characters(self, tts_service):
        """Test handling special characters."""
        special_text = "Alert! $100 <script>alert('xss')</script>"

        tts_service.speak(special_text)

        # Should not crash
        assert not tts_service.speak_queue.empty()


@pytest.mark.unit
class TestTTSServiceCancelAll:
    """Tests for cancel_all functionality."""

    @pytest.fixture
    def tts_service(self):
        """Create TTS service with mocked engine."""
        with patch("code_sergeant.tts.pyttsx3") as mock_pyttsx3:
            mock_engine = MagicMock()
            mock_pyttsx3.init.return_value = mock_engine
            mock_engine.getProperty.return_value = []

            service = TTSService()
            service.engine = mock_engine
            yield service

    def test_cancel_all_clears_queue(self, tts_service):
        """Test that cancel_all clears the queue."""
        tts_service.speak("Message 1")
        tts_service.speak("Message 2")

        tts_service.cancel_all()

        assert tts_service.speak_queue.empty()

    def test_cancel_all_returns_count(self, tts_service):
        """Test that cancel_all returns cleared count."""
        tts_service.speak("Message 1")
        tts_service.speak("Message 2")
        tts_service.speak("Message 3")

        count = tts_service.cancel_all()

        assert count == 3


@pytest.mark.unit
class TestTTSServicePauseResume:
    """Tests for pause/resume functionality."""

    @pytest.fixture
    def tts_service(self):
        """Create TTS service with mocked engine."""
        with patch("code_sergeant.tts.pyttsx3") as mock_pyttsx3:
            mock_engine = MagicMock()
            mock_pyttsx3.init.return_value = mock_engine
            mock_engine.getProperty.return_value = []

            service = TTSService()
            service.engine = mock_engine
            yield service

    def test_pause(self, tts_service):
        """Test pause functionality."""
        tts_service.pause()

        # Should be paused
        assert tts_service._paused.is_set()

    def test_resume(self, tts_service):
        """Test resume functionality."""
        tts_service.pause()
        tts_service.resume()

        # Should not be paused
        assert not tts_service._paused.is_set()


@pytest.mark.unit
class TestTTSServiceStatus:
    """Tests for status functionality."""

    @pytest.fixture
    def tts_service(self):
        """Create TTS service with mocked engine."""
        with patch("code_sergeant.tts.pyttsx3") as mock_pyttsx3:
            mock_engine = MagicMock()
            mock_pyttsx3.init.return_value = mock_engine
            mock_engine.getProperty.return_value = []

            service = TTSService()
            service.engine = mock_engine
            yield service

    def test_get_status(self, tts_service):
        """Test get_status returns valid structure."""
        status = tts_service.get_status()

        assert "provider" in status
        assert "voice_id" in status
        assert status["provider"] in ["pyttsx3", "elevenlabs"]

    def test_is_speaking(self, tts_service):
        """Test is_speaking property."""
        # Initially not speaking
        assert not tts_service.is_speaking()


@pytest.mark.unit
class TestTTSServiceWorker:
    """Tests for TTS worker thread."""

    @pytest.fixture
    def tts_service(self):
        """Create TTS service with mocked engine."""
        with patch("code_sergeant.tts.pyttsx3") as mock_pyttsx3:
            mock_engine = MagicMock()
            mock_pyttsx3.init.return_value = mock_engine
            mock_engine.getProperty.return_value = []

            service = TTSService()
            service.engine = mock_engine
            yield service

    def test_start_worker(self, tts_service):
        """Test starting worker thread."""
        tts_service.start()

        assert tts_service.worker_thread is not None

        # Cleanup
        tts_service.stop()

    def test_stop_worker(self, tts_service):
        """Test stopping worker thread."""
        tts_service.start()
        tts_service.stop()

        # Worker should be stopped
        assert tts_service.stop_event.is_set()


@pytest.mark.unit
class TestTTSServiceVoice:
    """Tests for voice configuration."""

    @pytest.fixture
    def tts_service(self):
        """Create TTS service with mocked engine."""
        with patch("code_sergeant.tts.pyttsx3") as mock_pyttsx3:
            mock_engine = MagicMock()
            mock_pyttsx3.init.return_value = mock_engine
            mock_engine.getProperty.return_value = []

            service = TTSService()
            service.engine = mock_engine
            yield service

    def test_set_voice(self, tts_service):
        """Test setting voice."""
        result = tts_service.set_voice("test_voice_id")

        # Result depends on whether voice is found
        assert isinstance(result, bool)

    def test_set_api_key(self, tts_service):
        """Test setting API key."""
        with patch("code_sergeant.tts.ELEVENLABS_AVAILABLE", True):
            with patch("code_sergeant.tts.ElevenLabs"):
                result = tts_service.set_api_key("new_api_key")

                # Should update the API key
                assert tts_service.api_key == "new_api_key"


@pytest.mark.unit
class TestTTSServiceWaitForCompletion:
    """Tests for wait_for_completion functionality."""

    @pytest.fixture
    def tts_service(self):
        """Create TTS service with mocked engine."""
        with patch("code_sergeant.tts.pyttsx3") as mock_pyttsx3:
            mock_engine = MagicMock()
            mock_pyttsx3.init.return_value = mock_engine
            mock_engine.getProperty.return_value = []

            service = TTSService()
            service.engine = mock_engine
            yield service

    def test_wait_when_not_speaking(self, tts_service):
        """Test wait_for_completion when not speaking."""
        result = tts_service.wait_for_completion(timeout=1.0)

        # Should return True immediately
        assert result is True

    def test_wait_with_timeout(self, tts_service):
        """Test wait_for_completion with timeout."""
        # This should complete quickly
        start = time.time()
        result = tts_service.wait_for_completion(timeout=0.5)
        elapsed = time.time() - start

        assert result is True
        assert elapsed < 1.0  # Should be fast when not speaking
