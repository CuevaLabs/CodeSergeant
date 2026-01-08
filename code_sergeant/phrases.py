"""Character phrases and canned reminders for Code Sergeant.

This module provides phrases used by the judge and other components.
For personality-aware phrase generation, use the PersonalityManager class.
"""
from typing import List, Optional, Dict, Any


def get_off_task_warnings() -> List[str]:
    """Get warning phrases for off-task behavior (default sergeant personality)."""
    return [
        "Hey! Stay focused on your goal.",
        "That's not what you're supposed to be doing.",
        "Get back to work, soldier!",
        "Focus up! You have a mission.",
        "Distraction detected. Return to task.",
    ]


def get_off_task_yells() -> List[str]:
    """Get more aggressive phrases for repeated off-task behavior (default sergeant personality)."""
    return [
        "Sergeant here! You're off track again!",
        "Enough distractions! Get back to work!",
        "This is your final warning. Focus!",
        "You're wasting time. Get back on task!",
    ]


def get_off_task_drill() -> List[str]:
    """Get drill phrases for continuous nagging when user is distracted (RED status)."""
    return [
        "Get off that distraction! Now!",
        "What are you doing?! Get back to work!",
        "This is unacceptable! Focus!",
        "Move it! Back to your task!",
        "Distraction alert! Eyes on the mission!",
        "Stop wasting time! Work!",
        "Hey! I said focus!",
        "Drop that and get back to it!",
        "You're still distracted! Come on!",
        "Time is ticking! Get moving!",
        "No excuses! Back to work!",
        "I'm not going to stop until you focus!",
        "Still slacking?! Unbelievable!",
        "Your goal isn't going to complete itself!",
        "Snap out of it! Work time!",
    ]


def get_on_task_phrases() -> List[str]:
    """Get encouragement phrases for being on task."""
    return [
        "Good work, soldier. Keep it up.",
        "That's what I like to see. Stay focused.",
        "Outstanding! Maintain this momentum.",
    ]


def get_thinking_phrases() -> List[str]:
    """Get phrases for when user appears to be thinking."""
    return [
        "Taking time to think? Approved. Stay sharp.",
        "Strategic pause acknowledged. Carry on.",
        "Good thinking. Take your time, but stay on track.",
    ]


def get_reminders() -> List[str]:
    """Get reminder phrases for periodic nudges."""
    return [
        "Time for a quick stretch break.",
        "Remember to drink some water.",
        "Take a moment to breathe.",
        "How's your progress? Stay focused.",
    ]


def get_session_summary_template() -> str:
    """Template for session summary."""
    return (
        "Session complete. "
        "Focus time: {focus_minutes} minutes. "
        "Distractions: {distractions}. "
        "Keep it up!"
    )


def get_pomodoro_work_complete_phrases() -> List[str]:
    """Get phrases for when a pomodoro work period completes."""
    return [
        "Work period complete! Time for a break.",
        "Pomodoro done! You've earned a rest.",
        "Excellent focus! Take a breather.",
    ]


def get_pomodoro_break_complete_phrases() -> List[str]:
    """Get phrases for when a break period completes."""
    return [
        "Break's over! Ready for another round?",
        "Time to get back to work!",
        "Recharged? Let's go!",
    ]


def get_voice_note_confirmation() -> List[str]:
    """Get phrases confirming a voice note was saved."""
    return [
        "Got it. I'll save that for later.",
        "Note saved.",
        "Recorded. You can check it in your logs.",
    ]


def get_distraction_acknowledgment() -> List[str]:
    """Get phrases acknowledging user-reported distractions."""
    return [
        "Thanks for being honest. Let's get back on track.",
        "Understood. Ready when you are.",
        "Noted. Now let's refocus.",
    ]


def get_phone_report_acknowledgment() -> List[str]:
    """Get phrases acknowledging phone usage report."""
    return [
        "Phone time logged. Ready to get back to work?",
        "Got it. Let's refocus now.",
        "Noted. Your goal is waiting for you.",
    ]


# Personality-specific phrase collections (used by PersonalityManager)
PERSONALITY_PHRASE_TYPES = [
    "off_task_warning",
    "off_task_yell",
    "off_task_drill",  # For continuous drilling when RED
    "on_task",
    "thinking",
    "reminder",
    "session_start",
    "session_end",
    "pomodoro_work_complete",
    "pomodoro_break_complete",
]
