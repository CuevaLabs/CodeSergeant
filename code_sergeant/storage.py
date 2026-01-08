"""Session log storage."""
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import asdict

from .models import SessionStats, VoiceNote, DistractionLog

logger = logging.getLogger("code_sergeant.storage")


def write_session_log(
    stats: SessionStats,
    goal: str,
    config_snapshot: Dict[str, Any],
    log_dir: str = "logs",
    personality_name: Optional[str] = None
) -> str:
    """
    Write session log to JSON file with enhanced data.
    
    Args:
        stats: Session statistics
        goal: Session goal
        config_snapshot: Configuration at session start
        log_dir: Directory to write logs
        personality_name: Current personality name
        
    Returns:
        Path to written log file
    """
    # Create logs directory if needed
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"session_{timestamp}.json"
    
    # Serialize voice notes
    voice_notes_data = []
    for note in stats.voice_notes:
        voice_notes_data.append({
            "timestamp": note.timestamp.isoformat(),
            "content": note.content,
            "transcription": note.transcription
        })
    
    # Serialize distraction logs
    distraction_logs_data = []
    for log_entry in stats.distraction_logs:
        distraction_logs_data.append({
            "timestamp": log_entry.timestamp.isoformat(),
            "reason": log_entry.reason,
            "is_phone": log_entry.is_phone
        })
    
    # Serialize phone reports
    phone_reports_data = [ts.isoformat() for ts in stats.phone_reports]
    
    # Calculate duration
    duration_seconds = None
    if stats.start_time and stats.end_time:
        duration_seconds = (stats.end_time - stats.start_time).total_seconds()
    
    # Prepare log data
    log_data = {
        "session": {
            "goal": goal,
            "start_time": stats.start_time.isoformat() if stats.start_time else None,
            "end_time": stats.end_time.isoformat() if stats.end_time else None,
            "duration_seconds": duration_seconds,
            "personality": personality_name
        },
        "stats": {
            "focus_seconds": stats.focus_seconds,
            "idle_seconds": stats.idle_seconds,
            "off_task_seconds": stats.off_task_seconds,
            "thinking_seconds": stats.thinking_seconds,
            "distractions_count": stats.distractions_count,
            "best_focus_streak_seconds": stats.best_focus_streak_seconds,
            "current_focus_streak_seconds": stats.current_focus_streak_seconds,
            "pomodoros_completed": stats.pomodoros_completed
        },
        "voice_notes": voice_notes_data,
        "distraction_logs": distraction_logs_data,
        "phone_reports": phone_reports_data,
        "annotations": stats.annotations,
        "config": config_snapshot,
        "timestamp": datetime.now().isoformat()
    }
    
    # Write to file
    try:
        with open(log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
        logger.info(f"Session log written to {log_file}")
        return str(log_file)
    except Exception as e:
        logger.error(f"Error writing session log: {e}")
        raise


def add_voice_note(stats: SessionStats, content: str, transcription: str = "") -> VoiceNote:
    """
    Add a voice note to session stats.
    
    Args:
        stats: Session statistics
        content: Note content
        transcription: Original transcription
        
    Returns:
        Created VoiceNote
    """
    note = VoiceNote(
        timestamp=datetime.now(),
        content=content,
        transcription=transcription
    )
    stats.voice_notes.append(note)
    logger.info(f"Voice note added: {content[:50]}...")
    return note


def add_distraction_log(stats: SessionStats, reason: str, is_phone: bool = False) -> DistractionLog:
    """
    Add a distraction log entry.
    
    Args:
        stats: Session statistics
        reason: Distraction reason
        is_phone: Whether distraction was phone-related
        
    Returns:
        Created DistractionLog
    """
    log_entry = DistractionLog(
        timestamp=datetime.now(),
        reason=reason,
        is_phone=is_phone
    )
    stats.distraction_logs.append(log_entry)
    
    if is_phone:
        stats.phone_reports.append(datetime.now())
    
    logger.info(f"Distraction logged: {reason} (phone: {is_phone})")
    return log_entry


def add_annotation(stats: SessionStats, annotation: str) -> None:
    """
    Add an annotation to session stats.
    
    Args:
        stats: Session statistics
        annotation: Annotation text
    """
    stats.annotations.append(annotation)
    logger.info(f"Annotation added: {annotation[:50]}...")


def load_session_logs(log_dir: str = "logs", limit: int = 10) -> List[Dict[str, Any]]:
    """
    Load recent session logs.
    
    Args:
        log_dir: Directory containing logs
        limit: Maximum number of logs to load
        
    Returns:
        List of session log dictionaries
    """
    log_path = Path(log_dir)
    if not log_path.exists():
        return []
    
    # Find session log files
    log_files = sorted(log_path.glob("session_*.json"), reverse=True)
    
    logs = []
    for log_file in log_files[:limit]:
        try:
            with open(log_file, 'r') as f:
                log_data = json.load(f)
                log_data['_file'] = str(log_file)
                logs.append(log_data)
        except Exception as e:
            logger.warning(f"Failed to load log {log_file}: {e}")
    
    return logs


def get_session_summary(stats: SessionStats) -> Dict[str, Any]:
    """
    Get a summary of session statistics.
    
    Args:
        stats: Session statistics
        
    Returns:
        Summary dictionary
    """
    total_seconds = stats.focus_seconds + stats.idle_seconds + stats.off_task_seconds + stats.thinking_seconds
    
    return {
        "total_minutes": total_seconds // 60,
        "focus_minutes": stats.focus_seconds // 60,
        "focus_percentage": (stats.focus_seconds / total_seconds * 100) if total_seconds > 0 else 0,
        "thinking_minutes": stats.thinking_seconds // 60,
        "off_task_minutes": stats.off_task_seconds // 60,
        "idle_minutes": stats.idle_seconds // 60,
        "distractions": stats.distractions_count,
        "voice_notes_count": len(stats.voice_notes),
        "pomodoros_completed": stats.pomodoros_completed,
        "best_focus_streak_minutes": stats.best_focus_streak_seconds // 60,
        "phone_distractions": len(stats.phone_reports)
    }


def save_note_to_file(content: str, notes_dir: str = "notes") -> str:
    """
    Save a note to a text file.
    
    Args:
        content: Note content to save
        notes_dir: Directory to save notes in
        
    Returns:
        Path to saved note file
    """
    # Create notes directory if needed
    notes_path = Path(notes_dir)
    notes_path.mkdir(exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    note_file = notes_path / f"note_{timestamp}.txt"
    
    # Write note to file
    try:
        with open(note_file, 'w', encoding='utf-8') as f:
            f.write(f"Note created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n\n")
            f.write(content)
            f.write("\n")
        logger.info(f"Note saved to {note_file}")
        return str(note_file)
    except Exception as e:
        logger.error(f"Error saving note to file: {e}")
        raise


def export_session_to_markdown(stats: SessionStats, goal: str, output_file: str = None) -> str:
    """
    Export session to markdown format.
    
    Args:
        stats: Session statistics
        goal: Session goal
        output_file: Optional output file path
        
    Returns:
        Markdown string
    """
    summary = get_session_summary(stats)
    
    md = f"""# Focus Session Report

## Goal
{goal}

## Duration
- **Start:** {stats.start_time.strftime('%Y-%m-%d %H:%M:%S') if stats.start_time else 'N/A'}
- **End:** {stats.end_time.strftime('%Y-%m-%d %H:%M:%S') if stats.end_time else 'N/A'}
- **Total:** {summary['total_minutes']} minutes

## Statistics
- Focus Time: {summary['focus_minutes']} minutes ({summary['focus_percentage']:.1f}%)
- Thinking Time: {summary['thinking_minutes']} minutes
- Off-Task Time: {summary['off_task_minutes']} minutes
- Idle Time: {summary['idle_minutes']} minutes
- Distractions: {summary['distractions']}
- Pomodoros Completed: {summary['pomodoros_completed']}
- Best Focus Streak: {summary['best_focus_streak_minutes']} minutes

"""
    
    if stats.voice_notes:
        md += "## Voice Notes\n"
        for note in stats.voice_notes:
            md += f"- [{note.timestamp.strftime('%H:%M')}] {note.content}\n"
        md += "\n"
    
    if stats.distraction_logs:
        md += "## Distraction Log\n"
        for log_entry in stats.distraction_logs:
            phone_tag = " 📱" if log_entry.is_phone else ""
            md += f"- [{log_entry.timestamp.strftime('%H:%M')}] {log_entry.reason}{phone_tag}\n"
        md += "\n"
    
    if stats.annotations:
        md += "## Notes\n"
        for annotation in stats.annotations:
            md += f"- {annotation}\n"
        md += "\n"
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(md)
        logger.info(f"Session exported to {output_file}")
    
    return md
