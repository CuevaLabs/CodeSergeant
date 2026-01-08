"""Pomodoro timer for Code Sergeant."""
import logging
import threading
import time
from typing import Optional, Callable, Dict, Any
from dataclasses import asdict

from .models import PomodoroState

logger = logging.getLogger("code_sergeant.pomodoro")


class PomodoroTimer:
    """Pomodoro timer with work/break cycles."""
    
    def __init__(
        self,
        work_duration_minutes: int = 25,
        short_break_minutes: int = 5,
        long_break_minutes: int = 15,
        pomodoros_until_long_break: int = 4,
        on_tick: Optional[Callable[[PomodoroState], None]] = None,
        on_state_change: Optional[Callable[[str, str], None]] = None,
        on_complete: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize pomodoro timer.
        
        Args:
            work_duration_minutes: Duration of work period in minutes
            short_break_minutes: Duration of short break in minutes
            long_break_minutes: Duration of long break in minutes
            pomodoros_until_long_break: Number of pomodoros before long break
            on_tick: Callback called every second with current state
            on_state_change: Callback called when state changes (old_state, new_state)
            on_complete: Callback called when a period completes (period_type)
        """
        self.state = PomodoroState(
            work_duration_minutes=work_duration_minutes,
            short_break_minutes=short_break_minutes,
            long_break_minutes=long_break_minutes,
            pomodoros_until_long_break=pomodoros_until_long_break,
        )
        
        self.on_tick = on_tick
        self.on_state_change = on_state_change
        self.on_complete = on_complete
        
        self._timer_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        
        logger.info(f"PomodoroTimer initialized: work={work_duration_minutes}m, "
                   f"short_break={short_break_minutes}m, long_break={long_break_minutes}m")
    
    @property
    def is_running(self) -> bool:
        """Check if timer is currently running (not stopped or paused)."""
        return (self.state.current_state != "stopped" and 
                not self.state.is_paused and
                self._timer_thread is not None and 
                self._timer_thread.is_alive())
    
    @property
    def display_time(self) -> str:
        """Get formatted time for display."""
        return self.state.get_display_time()
    
    @property
    def state_emoji(self) -> str:
        """Get emoji for current state."""
        return self.state.get_state_emoji()
    
    def start_work(self):
        """Start a work period."""
        with self._lock:
            old_state = self.state.current_state
            self.state.current_state = "work"
            self.state.time_remaining_seconds = self.state.work_duration_minutes * 60
            self.state.is_paused = False
            
            if self.on_state_change and old_state != "work":
                self.on_state_change(old_state, "work")
        
        self._start_timer()
        logger.info(f"Work period started: {self.state.work_duration_minutes} minutes")
    
    def start_short_break(self):
        """Start a short break."""
        with self._lock:
            old_state = self.state.current_state
            self.state.current_state = "short_break"
            self.state.time_remaining_seconds = self.state.short_break_minutes * 60
            self.state.is_paused = False
            
            if self.on_state_change and old_state != "short_break":
                self.on_state_change(old_state, "short_break")
        
        self._start_timer()
        logger.info(f"Short break started: {self.state.short_break_minutes} minutes")
    
    def start_long_break(self):
        """Start a long break."""
        with self._lock:
            old_state = self.state.current_state
            self.state.current_state = "long_break"
            self.state.time_remaining_seconds = self.state.long_break_minutes * 60
            self.state.is_paused = False
            
            if self.on_state_change and old_state != "long_break":
                self.on_state_change(old_state, "long_break")
        
        self._start_timer()
        logger.info(f"Long break started: {self.state.long_break_minutes} minutes")
    
    def pause(self):
        """Pause the timer."""
        with self._lock:
            if self.state.current_state != "stopped":
                self.state.is_paused = True
                self._stop_event.set()
                logger.info("Timer paused")
    
    def resume(self):
        """Resume the timer."""
        with self._lock:
            if self.state.is_paused and self.state.current_state != "stopped":
                self.state.is_paused = False
                self._start_timer()
                logger.info("Timer resumed")
    
    def stop(self):
        """Stop the timer completely."""
        with self._lock:
            old_state = self.state.current_state
            self._stop_event.set()
            self.state.current_state = "stopped"
            self.state.time_remaining_seconds = 0
            self.state.is_paused = False
            
            if self.on_state_change and old_state != "stopped":
                self.on_state_change(old_state, "stopped")
        
        if self._timer_thread and self._timer_thread.is_alive():
            self._timer_thread.join(timeout=2.0)
        
        logger.info("Timer stopped")
    
    def reset(self):
        """Reset the timer to initial state."""
        self.stop()
        with self._lock:
            self.state.pomodoros_completed = 0
        logger.info("Timer reset")
    
    def skip(self):
        """Skip to the next phase."""
        current = self.state.current_state
        if current == "work":
            self._complete_work()
        elif current in ("short_break", "long_break"):
            self._complete_break()
        logger.info(f"Skipped {current}")
    
    def _start_timer(self):
        """Start the timer thread."""
        self._stop_event.clear()
        
        if self._timer_thread and self._timer_thread.is_alive():
            self._stop_event.set()
            self._timer_thread.join(timeout=2.0)
            self._stop_event.clear()
        
        self._timer_thread = threading.Thread(target=self._timer_loop, daemon=True)
        self._timer_thread.start()
    
    def _timer_loop(self):
        """Main timer loop."""
        while not self._stop_event.is_set():
            with self._lock:
                if self.state.time_remaining_seconds <= 0:
                    self._handle_completion()
                    return
                
                self.state.time_remaining_seconds -= 1
                
                if self.on_tick:
                    # Create a copy of state for callback
                    state_copy = PomodoroState(**asdict(self.state))
                    self.on_tick(state_copy)
            
            # Wait for 1 second or until stopped
            if self._stop_event.wait(timeout=1.0):
                return
    
    def _handle_completion(self):
        """Handle completion of current period."""
        current = self.state.current_state
        
        if current == "work":
            self._complete_work()
        elif current in ("short_break", "long_break"):
            self._complete_break()
    
    def _complete_work(self):
        """Complete a work period."""
        with self._lock:
            self.state.pomodoros_completed += 1
            
            if self.on_complete:
                self.on_complete("work")
            
            # Determine if next break is short or long
            if self.state.pomodoros_completed % self.state.pomodoros_until_long_break == 0:
                self.state.current_state = "long_break"
                self.state.time_remaining_seconds = self.state.long_break_minutes * 60
                logger.info(f"Work complete! Starting long break. Pomodoros: {self.state.pomodoros_completed}")
            else:
                self.state.current_state = "short_break"
                self.state.time_remaining_seconds = self.state.short_break_minutes * 60
                logger.info(f"Work complete! Starting short break. Pomodoros: {self.state.pomodoros_completed}")
            
            if self.on_state_change:
                self.on_state_change("work", self.state.current_state)
        
        # Auto-start break
        self._start_timer()
    
    def _complete_break(self):
        """Complete a break period."""
        with self._lock:
            old_state = self.state.current_state
            
            if self.on_complete:
                self.on_complete(old_state)
            
            # Return to stopped state after break
            self.state.current_state = "stopped"
            self.state.time_remaining_seconds = 0
            
            if self.on_state_change:
                self.on_state_change(old_state, "stopped")
            
            logger.info("Break complete! Timer stopped, ready for next work period.")
    
    def get_state_dict(self) -> Dict[str, Any]:
        """Get current state as dictionary."""
        with self._lock:
            return asdict(self.state)
    
    def get_status_text(self) -> str:
        """Get human-readable status text."""
        state = self.state.current_state
        time_str = self.display_time
        
        if state == "stopped":
            return "Ready"
        elif state == "work":
            prefix = "⏸️ " if self.state.is_paused else "🍅 "
            return f"{prefix}Work: {time_str}"
        elif state == "short_break":
            prefix = "⏸️ " if self.state.is_paused else "☕ "
            return f"{prefix}Break: {time_str}"
        elif state == "long_break":
            prefix = "⏸️ " if self.state.is_paused else "🌴 "
            return f"{prefix}Long Break: {time_str}"
        return time_str


def create_pomodoro_from_config(config: Dict[str, Any], **callbacks) -> PomodoroTimer:
    """
    Create a PomodoroTimer from config.
    
    Args:
        config: Configuration dictionary
        **callbacks: Callback functions (on_tick, on_state_change, on_complete)
        
    Returns:
        Configured PomodoroTimer
    """
    pomodoro_config = config.get("pomodoro", {})
    
    return PomodoroTimer(
        work_duration_minutes=pomodoro_config.get("work_duration_minutes", 25),
        short_break_minutes=pomodoro_config.get("short_break_minutes", 5),
        long_break_minutes=pomodoro_config.get("long_break_minutes", 15),
        pomodoros_until_long_break=pomodoro_config.get("pomodoros_until_long_break", 4),
        **callbacks
    )

