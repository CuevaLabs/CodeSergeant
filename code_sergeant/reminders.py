"""Reminder timer workers."""
import logging
import random
import threading
import time
from typing import List

from .phrases import get_reminders

logger = logging.getLogger("code_sergeant.reminders")


class ReminderWorker:
    """Worker that emits reminder events at configured intervals."""

    def __init__(self, intervals_sec: List[int], event_queue, stop_event):
        """
        Initialize reminder worker.

        Args:
            intervals_sec: List of reminder intervals in seconds
            event_queue: Queue to emit events to
            stop_event: Event to signal stop
        """
        self.intervals_sec = intervals_sec
        self.event_queue = event_queue
        self.stop_event = stop_event
        self.reminders = get_reminders()
        logger.info(f"ReminderWorker initialized with intervals: {intervals_sec}")

    def run(self):
        """Run reminder worker loop."""
        logger.info("ReminderWorker started")

        # Track when each reminder should fire
        reminder_times = []
        start_time = time.time()

        for interval in self.intervals_sec:
            reminder_times.append(start_time + interval)

        reminder_times.sort()  # Sort by time

        while not self.stop_event.is_set():
            current_time = time.time()

            # Check if any reminders should fire
            fired = []
            for i, reminder_time in enumerate(reminder_times):
                if current_time >= reminder_time:
                    # Fire reminder
                    message = random.choice(self.reminders)
                    self.event_queue.put(
                        {
                            "type": "reminder_triggered",
                            "message": message,
                            "timestamp": current_time,
                        }
                    )
                    logger.info(f"Reminder fired: {message}")
                    fired.append(i)

            # Remove fired reminders
            for i in reversed(fired):
                reminder_times.pop(i)

            # If all reminders fired, we're done
            if not reminder_times:
                logger.info("All reminders fired, ReminderWorker stopping")
                break

            # Sleep until next check (or stop event)
            next_check = min(reminder_times) - current_time
            if next_check > 0:
                self.stop_event.wait(timeout=min(next_check, 1.0))
            else:
                self.stop_event.wait(timeout=0.1)

        logger.info("ReminderWorker stopped")
