"""Menu bar UI for Code Sergeant using rumps."""
import logging
import os
import time
from pathlib import Path
from typing import Optional

import rumps

from .config import save_config, set_env_var
from .controller import AppController
from .dashboard import DashboardWindow, create_dashboard
from .personality import get_personality_choices

logger = logging.getLogger("code_sergeant.menu_bar")


def find_app_icon() -> Optional[str]:
    """Find app icon file if it exists."""
    # Check possible locations
    locations = [
        Path("assets/icon.png"),
        Path("assets/icon.icns"),
        Path(__file__).parent.parent / "assets" / "icon.png",
        Path(__file__).parent.parent / "assets" / "icon.icns",
    ]

    for loc in locations:
        if loc.exists():
            logger.info(f"Found app icon: {loc}")
            return str(loc)

    return None


class CodeSergeantApp(rumps.App):
    """Main menu bar application."""

    # Status icons
    STATUS_ICONS = {
        "default": "⚔️",
        "green": "🟢",
        "yellow": "🟡",
        "red": "🔴",
        "pomodoro_work": "🍅",
        "pomodoro_break": "☕",
    }

    def __init__(self):
        # Try to load custom icon
        icon_path = find_app_icon()

        super().__init__(
            name="Code Sergeant",
            title="⚔️",
            icon=icon_path,
            template=True,
            quit_button=None,  # Disable default quit - we add our own
        )

        self.controller = AppController()
        self._setup_menu()

        # Status icon state
        self.current_status = "default"
        self.yellow_flash_start_time: Optional[float] = None
        self.yellow_flash_duration = 5.0  # Flash yellow for 5 seconds

        # Create dashboard window
        self.dashboard: Optional[DashboardWindow] = create_dashboard(
            on_start=self._dashboard_start_session, on_end=self._dashboard_end_session
        )

        # Timer to poll controller state and process events
        self.timer = rumps.Timer(
            self._update_state, 0.5
        )  # Update every 0.5s for smooth updates
        self.timer.start()

        # Flag to show dashboard only once on startup
        self._dashboard_shown_on_startup = False

        logger.info("Menu bar app initialized")

    def _setup_menu(self):
        """Set up menu items."""
        # Skip if menu already set up (prevents duplicates)
        if hasattr(self, "_menu_setup") and self._menu_setup:
            return

        # Get current personality name for display
        personality_name = self.controller.state.personality_name.title()
        wake_word = self.controller.state.wake_word

        # Create dynamic menu items and store references for later updates
        self.talk_item = rumps.MenuItem(
            f"Talk to {personality_name}", callback=self._on_talk_to_assistant
        )
        self.wake_word_item = rumps.MenuItem(f"Wake word: {wake_word}", callback=None)

        self.menu = [
            # Session controls
            rumps.MenuItem("Start Session", callback=self._on_start_session),
            rumps.MenuItem("End Session", callback=self._on_end_session),
            None,  # Separator
            # Pomodoro controls
            (
                rumps.MenuItem("🍅 Pomodoro", callback=None),
                [
                    rumps.MenuItem("Start Work", callback=self._on_pomodoro_start_work),
                    rumps.MenuItem(
                        "Start Break", callback=self._on_pomodoro_start_break
                    ),
                    rumps.MenuItem("Pause", callback=self._on_pomodoro_pause),
                    rumps.MenuItem("Resume", callback=self._on_pomodoro_resume),
                    rumps.MenuItem("Stop", callback=self._on_pomodoro_stop),
                    rumps.MenuItem("Skip", callback=self._on_pomodoro_skip),
                ],
            ),
            None,  # Separator
            # Voice interaction (use stored references)
            self.talk_item,
            self.wake_word_item,
            None,  # Separator
            # Settings submenu
            (
                rumps.MenuItem("⚙️ Settings", callback=None),
                [
                    (
                        rumps.MenuItem("Personality", callback=None),
                        [
                            rumps.MenuItem(
                                "🎖️ Drill Sergeant",
                                callback=lambda _: self._set_personality("sergeant"),
                            ),
                            rumps.MenuItem(
                                "👋 Friendly Buddy",
                                callback=lambda _: self._set_personality("buddy"),
                            ),
                            rumps.MenuItem(
                                "📋 Professional Advisor",
                                callback=lambda _: self._set_personality("advisor"),
                            ),
                            rumps.MenuItem(
                                "🏆 Motivational Coach",
                                callback=lambda _: self._set_personality("coach"),
                            ),
                            rumps.MenuItem(
                                "✨ Custom...", callback=self._on_custom_personality
                            ),
                        ],
                    ),
                    rumps.MenuItem(
                        "Voice Settings...", callback=self._on_voice_settings
                    ),
                    rumps.MenuItem("AI Settings...", callback=self._on_ai_settings),
                    rumps.MenuItem(
                        "Pomodoro Settings...", callback=self._on_pomodoro_settings
                    ),
                    rumps.MenuItem(
                        "Toggle Wake Word", callback=self._on_toggle_wake_word
                    ),
                    None,  # Separator
                    rumps.MenuItem(
                        "Toggle Screen Monitoring",
                        callback=self._on_screen_monitoring_toggle,
                    ),
                ],
            ),
            None,  # Separator
            # Logs and quit
            rumps.MenuItem("Open Logs", callback=self._on_open_logs),
            None,  # Separator
            rumps.MenuItem("Quit", callback=self._on_quit),
        ]

        # Mark menu as set up
        self._menu_setup = True

        # Initially disable End Session
        self.menu["End Session"].set_callback(None)

    def _update_state(self, _):
        """
        Update UI state from controller (non-blocking).
        Called by timer.
        """
        # Show dashboard on first tick (ensures app is fully ready)
        if not self._dashboard_shown_on_startup:
            self._show_dashboard_on_startup()

        # Process events from queue
        self.controller.process_events_tick()

        # Update menu based on state
        state = self.controller.get_state_snapshot()

        # Enable/disable menu items based on session state
        if state.session_active:
            self.menu["End Session"].set_callback(self._on_end_session)
            self.menu["Start Session"].set_callback(None)
        else:
            self.menu["End Session"].set_callback(None)
            self.menu["Start Session"].set_callback(self._on_start_session)
            # Reset status when session ends
            self.current_status = "default"
            self.yellow_flash_start_time = None

        # Update status icon based on judgment
        if state.session_active and state.last_judgment_obj:
            self._update_status_icon(state.last_judgment_obj)
        elif state.session_active:
            # Session active but no judgment yet - default
            self.current_status = "default"
            self.yellow_flash_start_time = None

        # Update title with status icon, pomodoro timer, and activity
        self._update_title(state)

        # Update personality-related menu items using stored references
        personality_name = state.personality_name.title()
        wake_word = state.wake_word

        # Update the "Talk to X" menu item title
        if hasattr(self, "talk_item") and self.talk_item:
            self.talk_item.title = f"Talk to {personality_name}"

        # Update wake word display
        if hasattr(self, "wake_word_item") and self.wake_word_item:
            indicator = "🎤 " if state.wake_word_active else ""
            self.wake_word_item.title = f"{indicator}Wake word: {wake_word}"

        # Update dashboard stats if session active
        if self.dashboard and state.session_active and state.stats:
            focus_min = state.stats.focus_seconds // 60
            distractions = state.stats.distractions_count

            # Determine status text
            status = "🟢 Session Active"
            if state.last_judgment_obj:
                if state.last_judgment_obj.classification == "off_task":
                    status = "🔴 Off Task!"
                elif state.last_judgment_obj.classification == "thinking":
                    status = "🤔 Thinking..."
                elif state.last_judgment_obj.classification == "on_task":
                    status = "🟢 Focused"

            self.dashboard.update_stats(focus_min, distractions, status)
            self.dashboard.is_session_active = True
        elif self.dashboard and not state.session_active:
            self.dashboard.is_session_active = False

    def _update_title(self, state):
        """Update the menu bar title."""
        status_icon = self._get_status_icon()

        # Build title components
        parts = [status_icon]

        # Add pomodoro timer if active
        if state.pomodoro_state and state.pomodoro_state.current_state != "stopped":
            pomodoro_display = state.pomodoro_state.get_display_time()
            pomodoro_emoji = state.pomodoro_state.get_state_emoji()
            if state.pomodoro_state.is_paused:
                parts.append(f"⏸️{pomodoro_display}")
            else:
                parts.append(f"{pomodoro_emoji}{pomodoro_display}")

        # Add activity if session active
        if state.session_active and state.current_activity:
            # Truncate activity if we have pomodoro showing
            max_len = (
                15
                if state.pomodoro_state
                and state.pomodoro_state.current_state != "stopped"
                else 25
            )
            parts.append(state.current_activity[:max_len])
        elif state.session_active:
            parts.append("Active")

        self.title = " ".join(parts)

    def _update_status_icon(self, judgment):
        """
        Update status icon based on judgment.

        Status logic (priority order):
        1. RED: off_task classification (user is distracted - will be drilled)
        2. YELLOW: warn action (temporary warning, flashes)
        3. GREEN: on_task or thinking classification (focused)
        4. DEFAULT: idle or unknown

        Args:
            judgment: Judgment object
        """
        classification = judgment.classification
        action = judgment.action

        # Priority 1: RED for off_task classification (user is distracted)
        # This persists until they return to on_task
        if classification == "off_task":
            self.current_status = "red"
            self.yellow_flash_start_time = None
            return

        # Priority 2: YELLOW for warn action (temporary flash to get attention)
        # Only show yellow if not already off_task
        if action == "warn" and classification != "off_task":
            if self.current_status != "yellow":
                self.yellow_flash_start_time = time.time()
            self.current_status = "yellow"
            return

        # Priority 3: GREEN for on_task or thinking (you're doing good!)
        if classification in ("on_task", "thinking"):
            self.current_status = "green"
            self.yellow_flash_start_time = None
            return

        # Priority 4: DEFAULT for idle, unknown, or anything else
        self.current_status = "default"
        self.yellow_flash_start_time = None

    def _get_status_icon(self) -> str:
        """
        Get the current status icon, handling yellow flashing.

        Returns:
            Status icon emoji
        """
        if self.current_status == "yellow" and self.yellow_flash_start_time:
            # Check if we should still flash (within duration)
            elapsed = time.time() - self.yellow_flash_start_time
            if elapsed < self.yellow_flash_duration:
                # Flash every 0.5 seconds (toggle on/off)
                flash_interval = 0.5
                flash_count = int(elapsed / flash_interval)
                # Toggle based on flash count
                if flash_count % 2 == 0:
                    return self.STATUS_ICONS["yellow"]
                else:
                    return self.STATUS_ICONS["default"]  # Flash to default
            else:
                # Flash duration expired, return to default
                self.current_status = "default"
                self.yellow_flash_start_time = None

        return self.STATUS_ICONS.get(self.current_status, self.STATUS_ICONS["default"])

    # === Dashboard Methods ===

    def _show_dashboard_on_startup(self):
        """Show dashboard window on app startup (called once)."""
        if self._dashboard_shown_on_startup:
            return
        self._dashboard_shown_on_startup = True

        if self.dashboard:
            self.dashboard.show(animate=True)
            logger.info("Dashboard shown on startup")

    def _dashboard_start_session(
        self, goal: str, work_minutes: int, break_minutes: int
    ):
        """Handle start session from dashboard."""
        # Update pomodoro settings
        self.controller.config["pomodoro"]["work_duration_minutes"] = work_minutes
        self.controller.config["pomodoro"]["short_break_minutes"] = break_minutes
        self.controller.pomodoro.state.work_duration_minutes = work_minutes
        self.controller.pomodoro.state.short_break_minutes = break_minutes

        # Start the session
        self.controller.start_session(goal)

        # Update menu state
        self.menu["End Session"].set_callback(self._on_end_session)
        self.menu["Start Session"].set_callback(None)

        # Notification
        rumps.notification(
            title="Code Sergeant", subtitle="Session Started", message=f"Goal: {goal}"
        )

        logger.info(f"Session started from dashboard: {goal}")

    def _dashboard_end_session(self):
        """Handle end session from dashboard."""
        # End the session
        self.controller.end_session()

        # Update menu state
        self.menu["End Session"].set_callback(None)
        self.menu["Start Session"].set_callback(self._on_start_session)

        # Hide dashboard with animation
        if self.dashboard:
            self.dashboard.hide(animate=True)

        # Notification
        rumps.notification(
            title="Code Sergeant",
            subtitle="Session Ended",
            message="Focus session completed",
        )

        logger.info("Session ended from dashboard")

    def _on_start_session(self, _):
        """Handle Start Session menu item click."""
        # Show dashboard window with unsuck animation
        if self.dashboard:
            self.dashboard.show(animate=True)
            logger.info("Dashboard shown from menu")
        else:
            # Fallback to rumps dialog if dashboard not available
            response = rumps.Window(
                "What's your focus goal for this session?",
                title="Start Focus Session",
                default_text="",
                dimensions=(400, 50),
            ).run()

            if response.clicked and response.text.strip():
                goal = response.text.strip()
                self.controller.start_session(goal)
                rumps.notification(
                    title="Code Sergeant",
                    subtitle="Session Started",
                    message=f"Goal: {goal}",
                )
            else:
                logger.info("Start session cancelled or empty goal")

    def _on_end_session(self, _):
        """Handle End Session menu item click."""
        # End session via dashboard handler (includes animation)
        self._dashboard_end_session()

    def _on_talk_to_assistant(self, _):
        """Handle Talk to Assistant menu item click."""
        # Trigger voice worker (non-blocking - runs in thread)
        try:
            self.controller.start_voice_interaction()
        except PermissionError as e:
            rumps.alert(title="Microphone Permission Required", message=str(e), ok="OK")
        except Exception as e:
            logger.error(f"Voice interaction error: {e}")
            rumps.alert(
                title="Voice Error",
                message=f"Failed to start voice interaction: {e}",
                ok="OK",
            )

    # Pomodoro controls
    def _on_pomodoro_start_work(self, _):
        """Start pomodoro work period."""
        self.controller.pomodoro.start_work()
        rumps.notification(
            title="Code Sergeant",
            subtitle="Pomodoro Started",
            message=f"Work for {self.controller.pomodoro.state.work_duration_minutes} minutes!",
        )

    def _on_pomodoro_start_break(self, _):
        """Start pomodoro break."""
        self.controller.pomodoro.start_short_break()

    def _on_pomodoro_pause(self, _):
        """Pause pomodoro."""
        self.controller.pomodoro.pause()

    def _on_pomodoro_resume(self, _):
        """Resume pomodoro."""
        self.controller.pomodoro.resume()

    def _on_pomodoro_stop(self, _):
        """Stop pomodoro."""
        self.controller.pomodoro.stop()

    def _on_pomodoro_skip(self, _):
        """Skip current pomodoro phase."""
        self.controller.pomodoro.skip()

    # Settings
    def _set_personality(self, personality_name: str):
        """Set personality."""
        self.controller.set_personality(personality_name)

        # Update menu items in place (avoid recreating menu which causes duplicates)
        if hasattr(self, "talk_item") and self.talk_item:
            self.talk_item.title = (
                f"Talk to {self.controller.state.personality_name.title()}"
            )
        if hasattr(self, "wake_word_item") and self.wake_word_item:
            wake_word = self.controller.state.wake_word
            indicator = "🎤 " if self.controller.state.wake_word_active else ""
            self.wake_word_item.title = f"{indicator}Wake word: {wake_word}"

        rumps.notification(
            title="Code Sergeant",
            subtitle="Personality Changed",
            message=f"Now using: {personality_name.title()}",
        )

    def _on_custom_personality(self, _):
        """Handle custom personality setup."""
        # Get custom wake word name
        name_response = rumps.Window(
            "What should I call myself? (This will be your wake word)",
            title="Custom Personality - Name",
            default_text="assistant",
            dimensions=(300, 30),
        ).run()

        if not name_response.clicked or not name_response.text.strip():
            return

        wake_word_name = name_response.text.strip().lower()

        # Get custom description
        desc_response = rumps.Window(
            "Describe how you'd like me to talk to you:",
            title="Custom Personality - Description",
            default_text="A friendly and supportive assistant who encourages me gently",
            dimensions=(400, 80),
        ).run()

        if not desc_response.clicked:
            return

        description = desc_response.text.strip()

        self.controller.set_personality("custom", description, wake_word_name)

        rumps.notification(
            title="Code Sergeant",
            subtitle="Custom Personality Set",
            message=f"Wake word: hey {wake_word_name}",
        )

    def _on_voice_settings(self, _):
        """Handle voice settings."""
        current_status = self.controller.tts_service.get_status()

        # Show current status
        provider = current_status.get("provider", "pyttsx3")
        api_key_set = current_status.get("api_key_set", False)

        message = f"Current provider: {provider}\n"
        if provider == "elevenlabs":
            message += f"API key: {'Set' if api_key_set else 'Not set'}\n"
            message += f"Voice ID: {current_status.get('voice_id', 'Default')}"

        response = rumps.Window(
            message,
            title="Voice Settings",
            default_text="",
            ok="Set ElevenLabs API Key",
            cancel="Close",
            dimensions=(400, 30),
        ).run()

        if response.clicked and response.text.strip():
            api_key = response.text.strip()
            success = self.controller.tts_service.set_api_key(api_key)

            if success:
                # SECURITY: save to .env, never to config.json
                set_env_var("ELEVENLABS_API_KEY", api_key)
                self.controller.config["tts"]["elevenlabs_api_key"] = None
                self.controller.config["tts"]["provider"] = "elevenlabs"
                save_config(self.controller.config)

                rumps.notification(
                    title="Code Sergeant",
                    subtitle="Voice Settings Updated",
                    message="ElevenLabs API key saved",
                )
            else:
                rumps.alert(title="Error", message="Failed to set API key", ok="OK")

    def _on_ai_settings(self, _):
        """Handle AI settings (OpenAI API key)."""
        ai_status = self.controller.ai_client.get_status()
        openai_available = ai_status.get("openai_available", False)
        key_present = bool(os.getenv("OPENAI_API_KEY"))

        message = (
            f"OpenAI key in .env: {'Yes' if key_present else 'No'}\n"
            f"OpenAI active: {'Yes' if openai_available else 'No'}\n"
            f"AI Backend: {'OpenAI' if openai_available else 'Ollama (local)'}\n"
        )
        if openai_available:
            message += f"Model: {ai_status.get('openai_model', 'gpt-4o-mini')}"
        else:
            message += f"Model: {ai_status.get('ollama_model', 'llama3.2')}\n"
            if key_present:
                message += "Key saved. Install `openai` and restart to enable OpenAI."
            else:
                message += "Enter your OpenAI API key to enable faster responses."

        response = rumps.Window(
            message,
            title="AI Settings",
            default_text="",
            ok="Set OpenAI API Key",
            cancel="Close",
            dimensions=(400, 30),
        ).run()

        if response.clicked and response.text.strip():
            api_key = response.text.strip()
            # SECURITY: save to .env, never to config.json
            set_env_var("OPENAI_API_KEY", api_key)

            # Update runtime client (will still work even if SDK isn't installed yet)
            success = self.controller.ai_client.set_openai_key(api_key)

            if success:
                # Ensure config never contains the key
                self.controller.config["openai"]["api_key"] = None
                save_config(self.controller.config)

                # If OpenAI SDK isn't installed yet, tell the user what to do
                updated_status = self.controller.ai_client.get_status()
                using_openai = updated_status.get("openai_available", False)
                rumps.notification(
                    title="Code Sergeant",
                    subtitle="AI Settings Updated",
                    message=(
                        "OpenAI enabled!"
                        if using_openai
                        else "Key saved to .env. Install `openai` and restart."
                    ),
                )
            else:
                rumps.alert(
                    title="Error", message="Failed to set OpenAI API key", ok="OK"
                )

    def _on_screen_monitoring_toggle(self, _):
        """Toggle screen monitoring on/off."""
        current = self.controller.screen_monitor.is_enabled()
        new_state = not current

        if new_state:
            # Show privacy warning before enabling
            result = rumps.alert(
                title="Enable Screen Monitoring?",
                message=(
                    "Screen monitoring captures periodic screenshots to analyze your progress.\n\n"
                    "Privacy protections:\n"
                    "• Screenshots are NEVER saved to disk\n"
                    "• Analysis uses local AI (images never leave your device)\n"
                    "• Sensitive apps (banking, passwords) are automatically blocked\n\n"
                    "Enable screen monitoring?"
                ),
                ok="Enable",
                cancel="Cancel",
            )
            if result != 1:  # User cancelled
                return

        self.controller.screen_monitor.enable(new_state)
        self.controller.config["screen_monitoring"]["enabled"] = new_state
        save_config(self.controller.config)

        rumps.notification(
            title="Code Sergeant",
            subtitle="Screen Monitoring",
            message=f"Screen monitoring {'enabled' if new_state else 'disabled'}",
        )

    def _on_pomodoro_settings(self, _):
        """Handle pomodoro settings."""
        current = self.controller.config.get("pomodoro", {})
        work_min = current.get("work_duration_minutes", 25)
        short_break = current.get("short_break_minutes", 5)
        long_break = current.get("long_break_minutes", 15)

        response = rumps.Window(
            f"Current: Work={work_min}min, Short break={short_break}min, Long break={long_break}min\n\n"
            "Enter new work duration (minutes):",
            title="Pomodoro Settings",
            default_text=str(work_min),
            dimensions=(300, 30),
        ).run()

        if response.clicked and response.text.strip():
            try:
                new_work = int(response.text.strip())
                if 1 <= new_work <= 120:
                    self.controller.config["pomodoro"][
                        "work_duration_minutes"
                    ] = new_work
                    self.controller.pomodoro.state.work_duration_minutes = new_work
                    save_config(self.controller.config)

                    rumps.notification(
                        title="Code Sergeant",
                        subtitle="Pomodoro Updated",
                        message=f"Work duration: {new_work} minutes",
                    )
            except ValueError:
                rumps.alert("Invalid number", ok="OK")

    def _on_toggle_wake_word(self, _):
        """Toggle wake word detection."""
        current = self.controller.config.get("voice_activation", {}).get(
            "enabled", False
        )
        new_state = not current

        self.controller.toggle_wake_word(new_state)

        rumps.notification(
            title="Code Sergeant",
            subtitle="Wake Word",
            message=f"Wake word detection {'enabled' if new_state else 'disabled'}",
        )

    def _on_open_logs(self, _):
        """Handle Open Logs menu item click."""
        import subprocess

        log_dir = os.path.join(os.getcwd(), "logs")
        if os.path.exists(log_dir):
            subprocess.run(["open", log_dir])
        else:
            rumps.alert("No logs directory found")

    def _on_quit(self, _):
        """Handle Quit menu item click."""
        # End session if active
        if self.controller.state.session_active:
            self.controller.end_session()

        # Stop timer
        self.timer.stop()

        # Stop wake word detector
        if self.controller.wake_word_detector:
            self.controller.wake_word_detector.stop()

        # Quit app
        rumps.quit_application()
