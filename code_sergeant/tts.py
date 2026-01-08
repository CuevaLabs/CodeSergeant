"""Text-to-speech service with ElevenLabs support."""
import logging
import os
import queue
import subprocess
import tempfile
import threading
from typing import Any, Dict, List, Optional

import pyttsx3

logger = logging.getLogger("code_sergeant.tts")

# Try to import ElevenLabs (optional) - v2 API
try:
    from elevenlabs.client import ElevenLabs

    ELEVENLABS_AVAILABLE = True
    logger.info("ElevenLabs SDK loaded successfully")
except ImportError as e:
    ELEVENLABS_AVAILABLE = False
    logger.warning(
        f"ElevenLabs not installed: {e}. Install with: pip install elevenlabs"
    )


# Common ElevenLabs voices for different personalities
RECOMMENDED_VOICES = {
    "sergeant": {
        "voice_id": "DGzg6RaUqxGRTHSBjfgF",
        "name": "Adam (Deep Male)",
        "description": "Deep, authoritative male voice",
    },
    "buddy": {
        "voice_id": "EXAVITQu4vr4xnSDxMaL",
        "name": "Sarah (Friendly Female)",
        "description": "Warm, friendly female voice",
    },
    "advisor": {
        "voice_id": "onwK4e9ZLuTAKqWW03F9",
        "name": "Daniel (British Male)",
        "description": "Professional, clear British male voice",
    },
    "coach": {
        "voice_id": "TX3LPaxmHKxFdv7VOQHJ",
        "name": "Liam (Energetic Male)",
        "description": "Energetic, motivational male voice",
    },
}


class TTSService:
    """Non-blocking text-to-speech service with ElevenLabs support."""

    def __init__(
        self,
        provider: str = "pyttsx3",
        api_key: Optional[str] = None,
        voice_id: Optional[str] = None,
        model_id: str = "eleven_turbo_v2_5",
        rate: int = 150,
        volume: float = 0.8,
    ):
        """
        Initialize TTS service.

        Args:
            provider: "elevenlabs" or "pyttsx3"
            api_key: ElevenLabs API key (required if provider is "elevenlabs")
            voice_id: Voice ID (ElevenLabs voice ID or pyttsx3 voice ID)
            model_id: ElevenLabs model ID (default: eleven_turbo_v2_5)
            rate: Speech rate (words per minute) - only for pyttsx3
            volume: Volume level (0.0-1.0) - only for pyttsx3
        """
        self.provider = provider.lower()
        self.api_key = api_key
        self.voice_id = voice_id
        self.model_id = model_id
        self.rate = rate
        self.volume = volume
        self.speak_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.worker_thread: Optional[threading.Thread] = None
        self.client = None
        self.engine = None  # pyttsx3 engine
        self._available_voices: Optional[List[Dict[str, Any]]] = None

        # State tracking for pause/wait functionality
        self._paused = threading.Event()
        self._speaking = threading.Event()  # Set when actively speaking
        self._speaking_done = threading.Event()
        self._speaking_done.set()  # Initially not speaking

        # Track current audio process for interruption
        self._current_process: Optional[subprocess.Popen] = None
        self._current_temp_file: Optional[str] = None

        # Initialize based on provider
        if self.provider == "elevenlabs":
            self._init_elevenlabs()
        else:
            self._init_pyttsx3()

    def _init_elevenlabs(self):
        """Initialize ElevenLabs TTS."""
        if not ELEVENLABS_AVAILABLE:
            logger.error("ElevenLabs not available, falling back to pyttsx3")
            self.provider = "pyttsx3"
            self._init_pyttsx3()
            return

        if not self.api_key:
            # Try to get from environment variable
            self.api_key = os.getenv("ELEVENLABS_API_KEY")
            if not self.api_key:
                logger.error("ElevenLabs API key not provided, falling back to pyttsx3")
                self.provider = "pyttsx3"
                self._init_pyttsx3()
                return

        try:
            # Initialize ElevenLabs client (v2 API)
            self.client = ElevenLabs(api_key=self.api_key)

            # Default voice ID if not provided (drill sergeant voice)
            if not self.voice_id:
                self.voice_id = "DGzg6RaUqxGRTHSBjfgF"

            # Also initialize pyttsx3 as fallback
            self._init_pyttsx3_fallback()

            logger.info(
                f"ElevenLabs TTS initialized with voice: {self.voice_id}, model: {self.model_id}"
            )
        except Exception as e:
            logger.error(
                f"Failed to initialize ElevenLabs: {e}, falling back to pyttsx3"
            )
            self.provider = "pyttsx3"
            self._init_pyttsx3()

    def _init_pyttsx3_fallback(self):
        """Initialize pyttsx3 as fallback (don't change provider)."""
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", self.rate)
            self.engine.setProperty("volume", self.volume)
            # Set Fred as fallback voice
            self._set_voice("com.apple.speech.synthesis.voice.Fred")
            logger.debug("pyttsx3 fallback initialized")
        except Exception as e:
            logger.warning(f"Could not initialize pyttsx3 fallback: {e}")
            self.engine = None

    def _init_pyttsx3(self):
        """Initialize pyttsx3 TTS (primary)."""
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", self.rate)
            self.engine.setProperty("volume", self.volume)

            # Set voice if specified and it's a pyttsx3 voice ID
            if self.voice_id and self.voice_id.startswith("com.apple"):
                self._set_voice(self.voice_id)
            else:
                # Default to Fred for drill sergeant feel
                self._set_voice("com.apple.speech.synthesis.voice.Fred")

            logger.info("pyttsx3 TTS engine initialized")
        except Exception as e:
            logger.error(f"Failed to initialize pyttsx3 engine: {e}")
            self.engine = None

    def _set_voice(self, voice_id: str) -> bool:
        """
        Set the pyttsx3 voice by ID.

        Args:
            voice_id: Voice identifier

        Returns:
            True if voice was set, False otherwise
        """
        if not self.engine:
            return False

        try:
            voices = self.engine.getProperty("voices")
            for voice in voices:
                if voice.id == voice_id or voice.name.lower() == voice_id.lower():
                    self.engine.setProperty("voice", voice.id)
                    logger.info(f"TTS voice set to: {voice.name}")
                    return True

            logger.warning(f"Voice not found: {voice_id}")
            return False
        except Exception as e:
            logger.error(f"Error setting voice: {e}")
            return False

    def set_voice(self, voice_id: str) -> bool:
        """
        Set the voice for TTS (public method).

        Args:
            voice_id: Voice ID (ElevenLabs or pyttsx3)

        Returns:
            True if voice was set successfully
        """
        self.voice_id = voice_id

        if self.provider == "elevenlabs":
            # For ElevenLabs, just update the voice_id
            logger.info(f"ElevenLabs voice set to: {voice_id}")
            return True
        else:
            return self._set_voice(voice_id)

    def set_api_key(self, api_key: str) -> bool:
        """
        Set ElevenLabs API key and reinitialize if needed.

        Args:
            api_key: ElevenLabs API key

        Returns:
            True if successful
        """
        self.api_key = api_key

        if self.provider == "elevenlabs" or (api_key and ELEVENLABS_AVAILABLE):
            try:
                self.client = ElevenLabs(api_key=api_key)
                self.provider = "elevenlabs"
                self._available_voices = None  # Reset cached voices
                logger.info("ElevenLabs API key updated and client reinitialized")
                return True
            except Exception as e:
                logger.error(f"Failed to reinitialize ElevenLabs with new API key: {e}")
                return False
        return True

    def get_available_voices(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get list of available voices.

        Args:
            force_refresh: Force refresh from API

        Returns:
            List of voice dictionaries with id, name, description
        """
        if self._available_voices and not force_refresh:
            return self._available_voices

        voices = []

        # Get ElevenLabs voices if available
        if self.provider == "elevenlabs" and self.client:
            try:
                response = self.client.voices.get_all()
                for voice in response.voices:
                    voices.append(
                        {
                            "id": voice.voice_id,
                            "name": voice.name,
                            "description": voice.description or "",
                            "provider": "elevenlabs",
                            "labels": getattr(voice, "labels", {}),
                        }
                    )
                logger.info(f"Fetched {len(voices)} ElevenLabs voices")
            except Exception as e:
                logger.warning(f"Failed to fetch ElevenLabs voices: {e}")

        # Get pyttsx3 voices
        if self.engine:
            try:
                pyttsx3_voices = self.engine.getProperty("voices")
                for voice in pyttsx3_voices:
                    voices.append(
                        {
                            "id": voice.id,
                            "name": voice.name,
                            "description": f"System voice ({voice.languages[0] if voice.languages else 'unknown'})",
                            "provider": "pyttsx3",
                        }
                    )
            except Exception as e:
                logger.warning(f"Failed to get pyttsx3 voices: {e}")

        self._available_voices = voices
        return voices

    def get_recommended_voice(self, personality: str) -> Dict[str, Any]:
        """
        Get recommended voice for a personality.

        Args:
            personality: Personality name (sergeant, buddy, advisor, coach)

        Returns:
            Voice info dictionary
        """
        return RECOMMENDED_VOICES.get(personality, RECOMMENDED_VOICES["sergeant"])

    def preview_voice(
        self, voice_id: str, text: str = "Hello! This is a voice preview."
    ) -> bool:
        """
        Preview a voice by speaking sample text.

        Args:
            voice_id: Voice ID to preview
            text: Sample text to speak

        Returns:
            True if preview successful
        """
        original_voice = self.voice_id
        try:
            self.voice_id = voice_id

            if self.provider == "elevenlabs" and self.client:
                self._speak_elevenlabs(text)
            elif self.engine:
                # Temporarily set voice for preview
                self._set_voice(voice_id)
                self.engine.say(text)
                self.engine.runAndWait()

            return True
        except Exception as e:
            logger.error(f"Voice preview failed: {e}")
            return False
        finally:
            self.voice_id = original_voice

    def start(self):
        """Start TTS worker thread."""
        if self.worker_thread and self.worker_thread.is_alive():
            logger.warning("TTS worker already running")
            return

        self.stop_event.clear()
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        logger.info("TTS worker started")

    def stop(self):
        """Stop TTS worker thread."""
        if self.worker_thread:
            self.stop_event.set()
            self.worker_thread.join(timeout=2.0)
            logger.info("TTS worker stopped")

    def speak(self, text: str) -> None:
        """
        Enqueue text to be spoken (non-blocking).

        Args:
            text: Text to speak
        """
        if not text or not text.strip():
            return

        try:
            self.speak_queue.put_nowait(text)
            logger.debug(f"Enqueued speech: {text[:50]}")
        except queue.Full:
            logger.warning("TTS queue full, dropping message")

    def pause(self) -> None:
        """
        Pause TTS queue processing.

        New items can still be enqueued but won't be spoken until resumed.
        """
        self._paused.set()
        logger.debug("TTS paused")

    def resume(self) -> None:
        """Resume TTS queue processing after pause."""
        self._paused.clear()
        logger.debug("TTS resumed")

    def clear_queue(self) -> int:
        """
        Clear all pending TTS messages from the queue.

        Returns:
            Number of messages cleared
        """
        count = 0
        try:
            while True:
                self.speak_queue.get_nowait()
                count += 1
        except queue.Empty:
            pass

        if count > 0:
            logger.info(f"Cleared {count} pending TTS messages")
        return count

    def wait_for_completion(self, timeout: float = 10.0) -> bool:
        """
        Wait until the current TTS message finishes speaking.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if completed, False if timed out
        """
        if not self._speaking.is_set():
            # Not currently speaking
            return True

        logger.debug("Waiting for TTS to complete...")
        result = self._speaking_done.wait(timeout=timeout)
        if result:
            logger.debug("TTS completed")
        else:
            logger.warning(f"TTS wait timed out after {timeout}s")
        return result

    def is_speaking(self) -> bool:
        """Check if TTS is currently speaking."""
        return self._speaking.is_set()

    def stop_current_audio(self) -> None:
        """
        Immediately stop currently playing audio.

        Terminates the afplay process if one is running.
        """
        if self._current_process and self._current_process.poll() is None:
            try:
                self._current_process.terminate()
                self._current_process.wait(
                    timeout=0.5
                )  # Wait briefly for clean termination
                logger.info("Stopped current audio playback")
            except Exception as e:
                logger.warning(f"Error terminating audio process: {e}")
                try:
                    self._current_process.kill()  # Force kill if terminate fails
                except Exception:
                    pass
            finally:
                self._current_process = None
                self._cleanup_temp_file()

    def cancel_all(self) -> int:
        """
        Stop current audio AND clear the queue.

        Use this when context changes (e.g., user returns to on_task)
        to immediately silence all pending and current speech.

        Returns:
            Number of messages cleared from queue
        """
        # First stop any currently playing audio
        self.stop_current_audio()

        # Then clear the queue
        cleared = self.clear_queue()

        # Reset speaking state
        self._speaking.clear()
        self._speaking_done.set()

        logger.info(
            f"Cancelled all TTS: stopped audio and cleared {cleared} queued messages"
        )
        return cleared

    def _cleanup_temp_file(self) -> None:
        """Clean up temporary audio file."""
        if self._current_temp_file:
            try:
                os.unlink(self._current_temp_file)
            except Exception:
                pass
            self._current_temp_file = None

    def _speak_elevenlabs(self, text: str):
        """Speak using ElevenLabs API (v2)."""
        try:
            # Generate audio using v2 API
            audio_gen = self.client.text_to_speech.convert(
                text=text, voice_id=self.voice_id, model_id=self.model_id
            )

            # Convert generator to bytes
            audio_bytes = b"".join(audio_gen)

            # Save to temp file and play with afplay (macOS)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(audio_bytes)
                temp_file = f.name

            # Track temp file for cleanup
            self._current_temp_file = temp_file

            # Play the audio using Popen (allows interruption)
            self._current_process = subprocess.Popen(["afplay", temp_file])
            self._current_process.wait()  # Block until done or terminated

            # Clean up temp file
            self._cleanup_temp_file()

            logger.debug(f"Spoke (ElevenLabs): {text[:50]}")
        except Exception as e:
            logger.error(f"Error speaking with ElevenLabs: {e}")
            self._current_process = None
            self._cleanup_temp_file()
            # Fallback to pyttsx3 if available
            if self.engine:
                try:
                    logger.info("Falling back to pyttsx3...")
                    self.engine.say(text)
                    self.engine.runAndWait()
                except Exception as e2:
                    logger.error(f"Fallback TTS also failed: {e2}")

    def _speak_pyttsx3(self, text: str):
        """Speak using pyttsx3."""
        if not self.engine:
            logger.warning(f"TTS engine not available, would speak: {text[:50]}")
            return

        try:
            self.engine.say(text)
            self.engine.runAndWait()
            logger.debug(f"Spoke (pyttsx3): {text[:50]}")
        except Exception as e:
            logger.error(f"Error speaking text: {e}")

    def _worker_loop(self):
        """Worker loop that processes speak queue."""
        logger.info("TTS worker loop started")

        while not self.stop_event.is_set():
            try:
                # Check if paused
                if self._paused.is_set():
                    self.stop_event.wait(timeout=0.1)
                    continue

                # Wait for text with timeout to check stop event
                try:
                    text = self.speak_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                # Check pause again after getting text (might have been paused while waiting)
                if self._paused.is_set():
                    # Put it back and wait
                    self.speak_queue.put(text)
                    continue

                # Mark as speaking
                self._speaking.set()
                self._speaking_done.clear()

                try:
                    # Speak using the configured provider
                    if self.provider == "elevenlabs" and self.client:
                        self._speak_elevenlabs(text)
                    else:
                        self._speak_pyttsx3(text)
                finally:
                    # Mark as done speaking
                    self._speaking.clear()
                    self._speaking_done.set()

            except Exception as e:
                logger.error(f"Error in TTS worker loop: {e}")
                self._speaking.clear()
                self._speaking_done.set()

        logger.info("TTS worker loop ended")

    def get_status(self) -> Dict[str, Any]:
        """
        Get current TTS service status.

        Returns:
            Status dictionary
        """
        return {
            "provider": self.provider,
            "voice_id": self.voice_id,
            "model_id": self.model_id if self.provider == "elevenlabs" else None,
            "elevenlabs_available": ELEVENLABS_AVAILABLE,
            "api_key_set": bool(self.api_key),
            "worker_running": self.worker_thread is not None
            and self.worker_thread.is_alive(),
        }


def get_elevenlabs_voices_for_ui() -> List[Dict[str, str]]:
    """
    Get simplified voice list for UI selection.

    Returns:
        List of voice options
    """
    voices = []

    # Add recommended voices first
    for personality, voice_info in RECOMMENDED_VOICES.items():
        voices.append(
            {
                "id": voice_info["voice_id"],
                "name": f"{voice_info['name']} (Recommended for {personality})",
                "personality": personality,
            }
        )

    return voices
