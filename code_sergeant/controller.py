"""AppController - manages session state and coordinates workers."""
import logging
import os
import queue
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .ai_client import AIClient, create_ai_client
from .config import get_personality_name, load_config, save_config, update_personality
from .judge import ActivityJudge
from .models import ActivityEvent, Judgment, PomodoroState, SessionStats
from .motivation_monitor import MotivationMonitor
from .native_monitor import NativeMonitor
from .personality import PersonalityManager, get_personality_choices
from .phrases import get_session_summary_template
from .pomodoro import PomodoroTimer, create_pomodoro_from_config
from .reminders import ReminderWorker
from .screen_monitor import ScreenMonitor, create_screen_monitor
from .storage import (
    add_annotation,
    add_distraction_log,
    add_voice_note,
    save_note_to_file,
    write_session_log,
)
from .tts import TTSService
from .voice import VoiceWorker, WakeWordDetector, run_voice_worker

logger = logging.getLogger("code_sergeant.controller")


@dataclass
class ControllerState:
    """Snapshot of controller state for UI rendering."""

    session_active: bool = False
    goal: Optional[str] = None
    current_activity: Optional[str] = None
    last_judgment: Optional[str] = None
    last_judgment_obj: Optional[Judgment] = None  # Full judgment object for UI
    stats: SessionStats = None
    pomodoro_state: Optional[PomodoroState] = None
    personality_name: str = "sergeant"
    wake_word: str = "hey sergeant"
    wake_word_active: bool = False

    def __post_init__(self):
        if self.stats is None:
            self.stats = SessionStats()


class AppController:
    """
    Central controller for Code Sergeant.

    Manages:
    - Session lifecycle (start/end)
    - State (goal, activity, stats)
    - Event queue processing
    - Worker thread coordination
    - Pomodoro timer
    - Voice commands and wake word detection
    - Personality management
    """

    def __init__(self):
        self.state = ControllerState()
        self.event_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.workers: Dict[str, threading.Thread] = {}

        # Load config
        self.config = load_config()

        # Initialize personality manager
        self.personality_manager = PersonalityManager(
            self.config,
            ollama_model=self.config["ollama"]["model"],
            ollama_base_url=self.config["ollama"]["base_url"],
        )

        # Update state with personality info
        self.state.personality_name = self.personality_manager.profile.name
        self.state.wake_word = self.personality_manager.wake_word

        # Initialize AI client first (OpenAI + Ollama fallback)
        self.ai_client = create_ai_client(self.config)

        # Initialize services
        self.native_monitor = NativeMonitor()
        self.judge = ActivityJudge(
            ai_client=self.ai_client,  # Use AIClient (prefers OpenAI if available)
            model=self.config["ollama"]["model"],
            base_url=self.config["ollama"]["base_url"],
            personality_manager=self.personality_manager,
        )
        self.tts_service = TTSService(
            provider=self.config["tts"].get("provider", "pyttsx3"),
            # SECURITY: read from environment; config is scrubbed to avoid leaking into logs
            api_key=os.getenv("ELEVENLABS_API_KEY")
            or self.config["tts"].get("elevenlabs_api_key")
            or self.config["tts"].get("api_key"),
            voice_id=self.config["tts"].get("voice_id"),
            model_id=self.config["tts"].get("model_id", "eleven_turbo_v2_5"),
            rate=self.config["tts"].get("rate", 150),
            volume=self.config["tts"].get("volume", 0.8),
        )
        self.tts_service.start()

        # Initialize pomodoro timer
        self.pomodoro = create_pomodoro_from_config(
            self.config,
            on_tick=self._on_pomodoro_tick,
            on_state_change=self._on_pomodoro_state_change,
            on_complete=self._on_pomodoro_complete,
        )

        # Voice worker (initialized lazily)
        self.voice_worker: Optional[VoiceWorker] = None

        # Wake word detector
        self.wake_word_detector: Optional[WakeWordDetector] = None
        self._init_wake_word_detector()

        # Start wake word detector if enabled (even without session)
        if self.wake_word_detector and self.config.get("voice_activation", {}).get(
            "enabled", False
        ):
            self.wake_word_detector.start()
            self.state.wake_word_active = True
            logger.info("Wake word detection started on initialization")

        # Session state
        self.current_activity: Optional[ActivityEvent] = None
        self.activity_history: list[ActivityEvent] = []
        self.last_judgment: Optional[Judgment] = None
        self.last_yell_time: Optional[float] = None

        # Drill worker for continuous nagging when off_task
        self.drill_worker: Optional[threading.Thread] = None
        self.drill_stop_event = threading.Event()
        self.drill_interval = (
            1.0  # Drill every 1 second when off_task for fast response
        )

        # Initialize motivation monitor
        self.motivation_monitor = MotivationMonitor(
            ai_client=self.ai_client,
            personality_manager=self.personality_manager,
            tts_service=self.tts_service,
            check_interval_minutes=self.config.get("motivation", {}).get(
                "check_interval_minutes", 3
            ),
        )

        # Initialize screen monitor (privacy-focused)
        self.screen_monitor = create_screen_monitor(
            config=self.config,
            native_monitor=self.native_monitor,
            ai_client=self.ai_client,
            tts_service=self.tts_service,
        )

        logger.info("AppController initialized")

    def _init_wake_word_detector(self):
        """Initialize wake word detector if enabled."""
        if self.config.get("voice_activation", {}).get("enabled", False):
            wake_words = [self.personality_manager.wake_word]
            self.wake_word_detector = WakeWordDetector(
                wake_words=wake_words,
                sensitivity=self.config.get("voice_activation", {}).get(
                    "sensitivity", 0.5
                ),
                on_wake_word=self._on_wake_word_detected,
                on_note_taking=self._on_note_taking_triggered,
            )
            logger.info(f"Wake word detector initialized with: {wake_words}")

    def _on_wake_word_detected(self, wake_word: str):
        """Handle wake word detection."""
        logger.info(f"Wake word detected: {wake_word}")
        self.event_queue.put(
            {
                "type": "wake_word_detected",
                "wake_word": wake_word,
                "timestamp": time.time(),
            }
        )
        # Automatically start voice interaction
        self.start_voice_interaction()

    def _on_note_taking_triggered(self, wake_word: str):
        """Handle note-taking wake word detection (e.g., 'hey sergeant take a note')."""
        logger.info(f"Note-taking triggered via wake word: {wake_word}")
        self.event_queue.put(
            {
                "type": "note_taking_triggered",
                "wake_word": wake_word,
                "timestamp": time.time(),
            }
        )
        # Start note-taking mode (longer recording)
        self.start_note_taking()

    def _on_pomodoro_tick(self, state: PomodoroState):
        """Handle pomodoro tick event."""
        self.state.pomodoro_state = state

    def _on_pomodoro_state_change(self, old_state: str, new_state: str):
        """Handle pomodoro state change."""
        logger.info(f"Pomodoro state changed: {old_state} -> {new_state}")

        # Announce state change
        if new_state == "work":
            phrase = self.personality_manager.get_phrase("session_start")
            self.tts_service.speak(phrase or "Work time! Focus up!")
        elif new_state == "short_break":
            self.tts_service.speak("Time for a short break!")
        elif new_state == "long_break":
            self.tts_service.speak("Great work! Time for a long break!")
        elif new_state == "stopped" and old_state in ("short_break", "long_break"):
            self.tts_service.speak("Break over! Ready for another round?")

    def _on_pomodoro_complete(self, period_type: str):
        """Handle pomodoro period completion."""
        logger.info(f"Pomodoro {period_type} complete")

        if period_type == "work" and self.state.stats:
            self.state.stats.pomodoros_completed += 1

    def start_session(self, goal: str) -> None:
        """
        Start a new focus session.

        Args:
            goal: User's stated goal for the session
        """
        if self.state.session_active:
            logger.warning("Session already active, ending previous session first")
            self.end_session()

        logger.info(f"Starting session with goal: {goal}")

        self.state.session_active = True
        self.state.goal = goal
        self.state.stats = SessionStats(start_time=datetime.now())

        # Reset state
        self.current_activity = None
        self.activity_history = []
        self.last_judgment = None
        self.last_yell_time = None

        # Reset judge patterns
        self.judge.reset_patterns()

        # Clear event queue
        while not self.event_queue.empty():
            try:
                self.event_queue.get_nowait()
            except queue.Empty:
                break

        # Start workers
        self._start_workers()

        # Auto-start pomodoro if configured
        if self.config.get("pomodoro", {}).get("auto_start_with_session", False):
            self.pomodoro.start_work()

        # Start wake word detector if configured
        if self.wake_word_detector and self.config.get("voice_activation", {}).get(
            "enabled", False
        ):
            self.wake_word_detector.start()
            self.state.wake_word_active = True

        # Start motivation monitor if enabled
        if self.config.get("motivation", {}).get("enabled", True):
            self.motivation_monitor.start(goal)

        # Start screen monitor if enabled
        if self.screen_monitor.is_enabled():
            self.screen_monitor.start(goal)

        # Announce session start
        phrase = self.personality_manager.get_phrase("session_start")
        self.tts_service.speak(phrase or "Session started!")

        logger.info("Session started")

    def end_session(self) -> None:
        """End the current session and stop all workers."""
        if not self.state.session_active:
            logger.warning("No active session to end")
            return

        logger.info("Ending session")

        # Signal workers to stop
        self.stop_event.set()

        # Stop drill worker and cancel all pending TTS
        self._stop_drill_worker()

        # Ensure all TTS is cancelled before session end
        self.tts_service.cancel_all()

        # Stop wake word detector
        if self.wake_word_detector:
            self.wake_word_detector.stop()
            self.state.wake_word_active = False

        # Stop pomodoro
        self.pomodoro.stop()

        # Stop motivation monitor
        self.motivation_monitor.stop()

        # Stop screen monitor
        self.screen_monitor.stop()

        # Wait for workers to stop (with timeout)
        for name, worker in self.workers.items():
            if worker.is_alive():
                logger.info(f"Waiting for worker {name} to stop...")
                worker.join(timeout=5.0)
                if worker.is_alive():
                    logger.warning(f"Worker {name} did not stop within timeout")

        # Update stats
        if self.state.stats.start_time:
            self.state.stats.end_time = datetime.now()
            self.state.stats.pomodoros_completed = (
                self.pomodoro.state.pomodoros_completed
            )

        # Write session log
        try:
            log_file = write_session_log(
                self.state.stats,
                self.state.goal or "Unknown",
                self.config,
                personality_name=self.state.personality_name,
            )
            logger.info(f"Session log written: {log_file}")
        except Exception as e:
            logger.error(f"Error writing session log: {e}")

        # Speak summary
        if self.state.stats.start_time and self.state.stats.end_time:
            focus_minutes = int(self.state.stats.focus_seconds / 60)
            phrase = self.personality_manager.get_phrase("session_end")
            summary = phrase or get_session_summary_template().format(
                focus_minutes=focus_minutes,
                distractions=self.state.stats.distractions_count,
            )
            self.tts_service.speak(summary)

        self.state.session_active = False

        # Reset stop event for next session
        self.stop_event.clear()

        logger.info("Session ended")

    def _start_drill_worker(self) -> None:
        """
        Start continuous drilling when user is distracted (off_task).

        Speaks a drill phrase every 5 seconds until user returns to on_task.
        """
        # Check if already running
        if self.drill_worker and self.drill_worker.is_alive():
            return

        self.drill_stop_event.clear()

        def drill_loop():
            """Continuously nag the user until they focus."""
            logger.info("Drill worker started - will nag every 5 seconds until focused")

            # Wait a bit before first drill (initial warning was already spoken)
            time.sleep(self.drill_interval)

            while not self.drill_stop_event.is_set() and self.state.session_active:
                # Check if still off_task
                if (
                    self.state.last_judgment_obj
                    and self.state.last_judgment_obj.classification == "off_task"
                ):
                    # Get a drill phrase and speak it
                    phrase = self.personality_manager.get_phrase("off_task_drill")
                    if phrase:
                        logger.info(f"Drilling: {phrase[:50]}...")
                        self.tts_service.speak(phrase)

                    # Wait for next drill
                    self.drill_stop_event.wait(self.drill_interval)
                else:
                    # User is back on task, stop drilling
                    logger.info("User back on task, stopping drill")
                    break

            logger.info("Drill worker stopped")

        self.drill_worker = threading.Thread(target=drill_loop, daemon=True)
        self.drill_worker.start()

    def _stop_drill_worker(self) -> None:
        """Stop the drill worker thread and cancel all pending/playing audio."""
        if self.drill_worker and self.drill_worker.is_alive():
            self.drill_stop_event.set()
            # Cancel all TTS (stop current audio + clear queue)
            self.tts_service.cancel_all()
            self.drill_worker.join(timeout=2.0)
            logger.info("Drill worker stopped and TTS cancelled")

    def _trigger_immediate_judgment(self) -> None:
        """
        Trigger an immediate judgment of current activity.

        Used when activity changes while drilling to quickly stop
        drilling if user returns to productive work.
        """
        if not self.state.session_active or not self.current_activity:
            return

        try:
            # Perform judgment immediately
            judgment = self.judge.judge(
                goal=self.state.goal or "",
                activity=self.current_activity,
                history=self.activity_history,
                last_yell_time=self.last_yell_time,
                cooldown_seconds=self.config["cooldown_seconds"],
            )

            if judgment:
                # Update judgment state directly (skip event queue for speed)
                self.last_judgment = judgment
                self.state.last_judgment = (
                    f"{judgment.classification} ({judgment.confidence:.0%})"
                )
                self.state.last_judgment_obj = judgment

                logger.info(
                    f"Immediate judgment: {judgment.classification} ({judgment.confidence:.0%})"
                )

                # If now on_task or thinking, stop drilling immediately
                if judgment.classification in ("on_task", "thinking"):
                    self._stop_drill_worker()
                    # Cancel all TTS (stop current audio + clear queue)
                    self.tts_service.cancel_all()
                    logger.info("Stopped drilling - user back on task")

        except Exception as e:
            logger.error(f"Error in immediate judgment: {e}")

    def pause_session(self) -> None:
        """Pause the current session."""
        if not self.state.session_active:
            return

        # Pause pomodoro if running
        if self.pomodoro.is_running:
            self.pomodoro.pause()

        self.tts_service.speak("Session paused.")
        logger.info("Session paused")

    def resume_session(self) -> None:
        """Resume the current session."""
        if not self.state.session_active:
            return

        # Resume pomodoro if paused
        if self.pomodoro.state.is_paused:
            self.pomodoro.resume()

        self.tts_service.speak("Session resumed. Let's go!")
        logger.info("Session resumed")

    def change_goal(self, new_goal: str) -> None:
        """Change the session goal."""
        old_goal = self.state.goal
        self.state.goal = new_goal

        # Log the goal change as an annotation
        if self.state.stats:
            add_annotation(
                self.state.stats, f"Goal changed from '{old_goal}' to '{new_goal}'"
            )

        self.tts_service.speak(f"Goal updated to: {new_goal}")
        logger.info(f"Goal changed: {old_goal} -> {new_goal}")

    def save_voice_note(self, content: str, transcription: str = "") -> None:
        """Save a voice note to both session stats and a text file."""
        # Save to session stats if session is active
        if self.state.stats:
            add_voice_note(self.state.stats, content, transcription)

        # Always save to text file (works even without session)
        try:
            note_file = save_note_to_file(content)
            self.tts_service.speak(f"Note saved to {Path(note_file).name}")
            logger.info(f"Voice note saved to file: {note_file}")
        except Exception as e:
            logger.error(f"Error saving note to file: {e}")
            self.tts_service.speak("Note saved to session, but failed to save to file.")

    def report_distraction(self, reason: str, is_phone: bool = False) -> None:
        """Report a distraction."""
        if self.state.stats:
            add_distraction_log(self.state.stats, reason, is_phone)
            self.state.stats.distractions_count += 1

            phrase = self.personality_manager.get_phrase("off_task_warning")
            self.tts_service.speak(phrase or "Thanks for being honest. Let's refocus!")

    def set_personality(
        self,
        personality_name: str,
        custom_description: str = None,
        custom_wake_word: str = None,
    ) -> None:
        """
        Change the personality.

        Args:
            personality_name: Name of personality
            custom_description: Description for custom personality
            custom_wake_word: Wake word for custom personality
        """
        # Update config
        self.config = update_personality(
            self.config, personality_name, custom_description, custom_wake_word
        )

        # Update personality manager
        self.personality_manager.set_personality(
            personality_name, custom_description, custom_wake_word
        )

        # Update state
        self.state.personality_name = self.personality_manager.profile.name
        self.state.wake_word = self.personality_manager.wake_word

        # Update wake word detector
        if self.wake_word_detector:
            self.wake_word_detector.set_wake_words([self.personality_manager.wake_word])

        # Update judge
        self.judge.set_personality_manager(self.personality_manager)

        logger.info(f"Personality changed to: {personality_name}")
        self.tts_service.speak(
            f"Personality changed. Say '{self.state.wake_word}' to talk to me!"
        )

    def toggle_wake_word(self, enabled: bool) -> None:
        """Toggle wake word detection."""
        self.config["voice_activation"]["enabled"] = enabled
        save_config(self.config)

        if enabled:
            if not self.wake_word_detector:
                self._init_wake_word_detector()
            # Start wake word detector regardless of session state
            if self.wake_word_detector:
                self.wake_word_detector.start()
                self.state.wake_word_active = True
                logger.info("Wake word detection started")
        else:
            if self.wake_word_detector:
                self.wake_word_detector.stop()
                self.state.wake_word_active = False

        logger.info(f"Wake word detection: {'enabled' if enabled else 'disabled'}")

    def process_events_tick(self) -> None:
        """
        Process pending events from the queue (non-blocking).
        Called periodically from UI thread.
        """
        try:
            while True:
                try:
                    event = self.event_queue.get_nowait()
                    self._handle_event(event)
                except queue.Empty:
                    break
        except Exception as e:
            logger.error(f"Error processing events: {e}", exc_info=True)

    def _handle_event(self, event: Dict[str, Any]) -> None:
        """
        Handle a single event from the queue.

        Args:
            event: Event dictionary with 'type' key
        """
        event_type = event.get("type")

        if event_type == "activity_update":
            self._handle_activity_update(event)
        elif event_type == "judgment_update":
            self._handle_judgment_update(event)
        elif event_type == "reminder_triggered":
            self._handle_reminder(event)
        elif event_type == "voice_command":
            self._handle_voice_command(event)
        elif event_type == "voice_transcript":
            self._handle_voice_transcript(event)
        elif event_type == "wake_word_detected":
            self._handle_wake_word(event)
        elif event_type == "note_taking_triggered":
            self._handle_note_taking(event)
        elif event_type == "error_event":
            self._handle_error(event)
        else:
            logger.warning(f"Unknown event type: {event_type}")

    def _handle_activity_update(self, event: Dict[str, Any]) -> None:
        """Handle activity update event."""
        activity = event.get("activity")
        if isinstance(activity, dict):
            # Convert dict to ActivityEvent if needed
            activity = ActivityEvent(**activity)

        self.current_activity = activity
        self.activity_history.append(activity)

        # Keep only last 10 activities
        if len(self.activity_history) > 10:
            self.activity_history.pop(0)

        # Update UI state
        if activity:
            self.state.current_activity = f"{activity.app} — {activity.title}"
        else:
            self.state.current_activity = "Unknown activity"

        logger.debug(f"Activity updated: {self.state.current_activity}")

        # Record app change for motivation monitor
        if activity:
            self.motivation_monitor.record_app_change(activity.app)

        # If drill worker is active, trigger immediate judgment check
        # This ensures we stop drilling IMMEDIATELY when user returns to productive app
        if self.drill_worker and self.drill_worker.is_alive():
            self._trigger_immediate_judgment()

    def _handle_judgment_update(self, event: Dict[str, Any]) -> None:
        """Handle judgment update event."""
        judgment = event.get("judgment")
        if isinstance(judgment, dict):
            judgment = Judgment(**judgment)

        self.last_judgment = judgment

        if judgment:
            self.state.last_judgment = (
                f"{judgment.classification} ({judgment.confidence:.0%})"
            )
            self.state.last_judgment_obj = judgment

            # Update stats based on judgment
            if judgment.classification == "off_task":
                self.state.stats.distractions_count += 1
                if judgment.action == "yell":
                    self.last_yell_time = time.time()

                # Start continuous drilling when off_task (RED status)
                self._start_drill_worker()
            else:
                # Stop drilling when back on task
                self._stop_drill_worker()

            # Trigger TTS if action requires it (first warning/yell)
            if judgment.action == "warn" or judgment.action == "yell":
                if judgment.say:
                    self.tts_service.speak(judgment.say)

        logger.debug(f"Judgment updated: {self.state.last_judgment}")

    def _handle_reminder(self, event: Dict[str, Any]) -> None:
        """Handle reminder event."""
        message = event.get("message")
        if not message:
            message = self.personality_manager.get_phrase("reminder")
        logger.info(f"Reminder: {message}")
        self.tts_service.speak(message)

    def _handle_voice_command(self, event: Dict[str, Any]) -> None:
        """Handle voice command event."""
        command = event.get("command")
        args = event.get("args")

        logger.info(f"Voice command: {command} (args: {args})")

        if command == "start_session" and args:
            self.start_session(args)
        elif command == "end_session":
            self.end_session()
        elif command == "pause_session":
            self.pause_session()
        elif command == "resume_session":
            self.resume_session()
        elif command == "change_goal" and args:
            self.change_goal(args)
        elif command == "save_note" and args:
            self.save_voice_note(args, event.get("transcript", ""))
        elif command == "start_note_taking":
            # User said "take a note" without content - start VAD recording
            self.start_note_taking()
        elif command == "report_distraction" and args:
            self.report_distraction(args)
        elif command == "report_phone":
            self.report_distraction("Phone usage", is_phone=True)
        elif command == "start_pomodoro":
            self.pomodoro.start_work()
        elif command == "pause_pomodoro":
            self.pomodoro.pause()
        elif command == "stop_pomodoro":
            self.pomodoro.stop()
        elif command == "skip_pomodoro":
            self.pomodoro.skip()
        elif command == "status":
            self._speak_status()

    def _handle_voice_transcript(self, event: Dict[str, Any]) -> None:
        """Handle voice transcript (non-command)."""
        transcript = event.get("transcript")
        logger.info(f"Voice transcript: {transcript}")
        # Non-command transcripts are handled by VoiceWorker with LLM response

    def _handle_wake_word(self, event: Dict[str, Any]) -> None:
        """Handle wake word detection event."""
        wake_word = event.get("wake_word")
        logger.info(f"Wake word event: {wake_word}")
        # Voice interaction is auto-started in _on_wake_word_detected

    def _handle_note_taking(self, event: Dict[str, Any]) -> None:
        """Handle note-taking trigger event."""
        wake_word = event.get("wake_word")
        logger.info(f"Note-taking event: {wake_word}")
        # Note-taking is auto-started in _on_note_taking_triggered

    def _handle_error(self, event: Dict[str, Any]) -> None:
        """Handle error event."""
        error_msg = event.get("message", "Unknown error")
        logger.error(f"Error event: {error_msg}")

    def _speak_status(self) -> None:
        """Speak current status."""
        if not self.state.session_active:
            self.tts_service.speak("No active session.")
            return

        focus_minutes = self.state.stats.focus_seconds // 60
        distractions = self.state.stats.distractions_count
        pomodoros = self.state.stats.pomodoros_completed

        status = f"You've focused for {focus_minutes} minutes with {distractions} distractions."
        if pomodoros > 0:
            status += f" {pomodoros} pomodoros completed."

        self.tts_service.speak(status)

    def start_voice_interaction(self) -> None:
        """Start voice interaction (push-to-talk or wake word triggered)."""
        # Stop wake word detector to avoid microphone conflicts
        wake_word_was_active = self.state.wake_word_active
        if self.wake_word_detector and wake_word_was_active:
            self.wake_word_detector.stop()
            self.state.wake_word_active = False
            logger.info("Wake word detector paused for voice interaction")

        # Initialize voice worker if needed
        if not self.voice_worker:
            self.voice_worker = VoiceWorker(
                record_seconds=self.config["voice"]["record_seconds"],
                sample_rate=self.config["voice"]["sample_rate"],
                ollama_model=self.config["ollama"]["model"],
                ollama_base_url=self.config["ollama"]["base_url"],
                tts_service=self.tts_service,
                personality_manager=self.personality_manager,
            )

        # Get current context
        goal = self.state.goal
        current_activity_str = self.state.current_activity

        # Run voice worker in thread
        def voice_thread():
            try:
                # Clear any pending TTS messages before recording
                self.tts_service.clear_queue()
                self.tts_service.wait_for_completion(timeout=5.0)

                run_voice_worker(
                    self.voice_worker, goal, current_activity_str, self.event_queue
                )
            except PermissionError:
                # Re-raise permission errors so UI can handle them
                raise
            except Exception as e:
                logger.error(f"Voice interaction error: {e}")
                self.event_queue.put(
                    {"type": "error_event", "message": f"Voice error: {e}"}
                )
            finally:
                # Resume wake word detector if it was active
                if wake_word_was_active and self.wake_word_detector:
                    time.sleep(0.3)  # Brief pause before resuming
                    self.wake_word_detector.start()
                    self.state.wake_word_active = True
                    logger.info("Wake word detector resumed after voice interaction")

        thread = threading.Thread(target=voice_thread, daemon=True)
        thread.start()
        logger.info("Voice interaction started")

    def start_note_taking(self) -> None:
        """
        Start note-taking mode with VAD-based recording.

        Uses voice activity detection to record until silence is detected
        (after speech) or max duration is reached.
        """
        # Stop wake word detector to avoid microphone conflicts
        wake_word_was_active = self.state.wake_word_active
        if self.wake_word_detector and wake_word_was_active:
            self.wake_word_detector.stop()
            self.state.wake_word_active = False
            logger.info("Wake word detector paused for note-taking")

        # Note-taking max duration (default 2 minutes since we wait for stop phrase)
        max_note_duration = self.config.get("voice", {}).get("note_record_seconds", 120)

        # Initialize voice worker for note-taking
        note_worker = VoiceWorker(
            record_seconds=max_note_duration,  # Fallback duration
            sample_rate=self.config["voice"]["sample_rate"],
            ollama_model=self.config["ollama"]["model"],
            ollama_base_url=self.config["ollama"]["base_url"],
            tts_service=self.tts_service,
            personality_manager=self.personality_manager,
        )

        def note_taking_thread():
            try:
                # IMPORTANT: Clear any pending TTS messages (warnings/drills) before recording
                # to prevent them from bleeding into the note transcript
                cleared = self.tts_service.clear_queue()
                if cleared > 0:
                    logger.info(
                        f"Cleared {cleared} pending TTS messages before note-taking"
                    )

                # Wait for any currently-speaking TTS to finish
                self.tts_service.wait_for_completion(timeout=5.0)

                # Brief pause to ensure audio playback fully stops
                time.sleep(0.3)

                # Announce note-taking mode with instructions
                self.tts_service.speak("Go ahead. Say 'end note' when you're done.")

                # Wait for the instruction TTS to actually finish speaking
                self.tts_service.wait_for_completion(timeout=10.0)
                time.sleep(0.5)  # Additional buffer for audio system

                # Record until user says stop phrase (e.g., "end note")
                logger.info(
                    f"Note-taking: Recording until stop phrase (max {max_note_duration}s)..."
                )
                transcript = note_worker.record_note(max_duration=max_note_duration)

                if transcript and transcript.strip():
                    # Save the note
                    self.save_voice_note(transcript.strip())
                    logger.info(f"Note saved: {transcript[:50]}...")
                else:
                    self.tts_service.speak("I didn't catch that. Try again.")
                    logger.warning("Note-taking: Empty transcript")

            except PermissionError:
                raise
            except Exception as e:
                logger.error(f"Note-taking error: {e}")
                self.tts_service.speak("Sorry, there was an error saving your note.")
                self.event_queue.put(
                    {"type": "error_event", "message": f"Note-taking error: {e}"}
                )
            finally:
                # Resume wake word detector if it was active
                if wake_word_was_active and self.wake_word_detector:
                    time.sleep(0.3)  # Brief pause before resuming
                    self.wake_word_detector.start()
                    self.state.wake_word_active = True
                    logger.info("Wake word detector resumed after note-taking")

        thread = threading.Thread(target=note_taking_thread, daemon=True)
        thread.start()
        logger.info("Note-taking mode started")

    def _start_workers(self):
        """Start all worker threads."""

        # ActivityPoller worker
        def activity_poller_loop():
            logger.info("ActivityPoller started")
            poll_interval = self.config["poll_interval_sec"]
            last_activity = None

            while not self.stop_event.is_set():
                try:
                    activity = self.native_monitor.get_current_activity()

                    # Only emit if activity changed
                    if last_activity is None or (
                        activity.app != last_activity.app
                        or activity.title != last_activity.title
                    ):
                        self.event_queue.put(
                            {"type": "activity_update", "activity": activity}
                        )
                        last_activity = activity

                except Exception as e:
                    logger.error(f"Error in ActivityPoller: {e}")
                    self.event_queue.put(
                        {
                            "type": "error_event",
                            "message": f"Activity polling error: {e}",
                        }
                    )

                self.stop_event.wait(timeout=poll_interval)

            logger.info("ActivityPoller stopped")

        # JudgeWorker
        def judge_worker_loop():
            logger.info("JudgeWorker started")
            judge_interval = self.config["judge_interval_sec"]
            last_judged_activity_id = None
            current_judgment = None

            while not self.stop_event.is_set():
                try:
                    # Judge if activity changed or on interval
                    if self.current_activity:
                        # Use a simple ID to track if activity changed
                        current_activity_id = (
                            f"{self.current_activity.app}:{self.current_activity.title}"
                            if self.current_activity
                            else None
                        )

                        # Only re-judge if activity changed
                        if (
                            last_judged_activity_id != current_activity_id
                            or last_judged_activity_id is None
                        ):
                            current_judgment = self.judge.judge(
                                goal=self.state.goal or "",
                                activity=self.current_activity,
                                history=self.activity_history,
                                last_yell_time=self.last_yell_time,
                                cooldown_seconds=self.config["cooldown_seconds"],
                            )

                            self.event_queue.put(
                                {
                                    "type": "judgment_update",
                                    "judgment": current_judgment,
                                }
                            )

                            last_judged_activity_id = current_activity_id

                        # Update stats based on classification AND action
                        if current_judgment:
                            if current_judgment.action in ("warn", "yell"):
                                self.state.stats.off_task_seconds += judge_interval
                            elif current_judgment.classification == "on_task":
                                self.state.stats.focus_seconds += judge_interval
                                # Update focus streak
                                self.state.stats.current_focus_streak_seconds += (
                                    judge_interval
                                )
                                if (
                                    self.state.stats.current_focus_streak_seconds
                                    > self.state.stats.best_focus_streak_seconds
                                ):
                                    self.state.stats.best_focus_streak_seconds = (
                                        self.state.stats.current_focus_streak_seconds
                                    )
                            elif current_judgment.classification == "thinking":
                                self.state.stats.thinking_seconds += judge_interval
                                # Thinking counts towards focus streak
                                self.state.stats.current_focus_streak_seconds += (
                                    judge_interval
                                )
                                if (
                                    self.state.stats.current_focus_streak_seconds
                                    > self.state.stats.best_focus_streak_seconds
                                ):
                                    self.state.stats.best_focus_streak_seconds = (
                                        self.state.stats.current_focus_streak_seconds
                                    )
                            elif current_judgment.classification == "idle":
                                self.state.stats.idle_seconds += judge_interval
                                # Reset focus streak on idle
                                self.state.stats.current_focus_streak_seconds = 0
                            elif current_judgment.classification == "off_task":
                                self.state.stats.off_task_seconds += judge_interval
                                # Reset focus streak on off-task
                                self.state.stats.current_focus_streak_seconds = 0

                except Exception as e:
                    logger.error(f"Error in JudgeWorker: {e}")
                    self.event_queue.put(
                        {"type": "error_event", "message": f"Judge error: {e}"}
                    )

                self.stop_event.wait(timeout=judge_interval)

            logger.info("JudgeWorker stopped")

        # ReminderWorker
        reminder_worker = ReminderWorker(
            intervals_sec=self.config["reminder_intervals_sec"],
            event_queue=self.event_queue,
            stop_event=self.stop_event,
        )

        # Start worker threads
        self.workers["activity_poller"] = threading.Thread(
            target=activity_poller_loop, daemon=True
        )
        self.workers["judge_worker"] = threading.Thread(
            target=judge_worker_loop, daemon=True
        )
        self.workers["reminder_worker"] = threading.Thread(
            target=reminder_worker.run, daemon=True
        )

        for name, worker in self.workers.items():
            worker.start()
            logger.info(f"Started worker: {name}")

    def get_state_snapshot(self) -> ControllerState:
        """
        Get current state snapshot for UI rendering.

        Returns:
            ControllerState snapshot
        """
        return ControllerState(
            session_active=self.state.session_active,
            goal=self.state.goal,
            current_activity=self.state.current_activity,
            last_judgment=self.state.last_judgment,
            last_judgment_obj=self.last_judgment,
            stats=self.state.stats,
            pomodoro_state=self.pomodoro.state if self.pomodoro else None,
            personality_name=self.state.personality_name,
            wake_word=self.state.wake_word,
            wake_word_active=self.state.wake_word_active,
        )

    def get_pomodoro_display(self) -> str:
        """Get pomodoro timer display string."""
        return self.pomodoro.get_status_text()

    def get_personality_choices(self):
        """Get available personality choices."""
        return get_personality_choices()
