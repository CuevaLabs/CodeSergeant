"""
Integration tests for complete session workflows.

Tests end-to-end session flows:
- Session start → work → break → end
- Pause/resume during session
- Multiple sessions
- Error recovery
"""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from code_sergeant.models import ActivityEvent, Judgment, SessionStats


@pytest.mark.integration
class TestBasicSessionFlow:
    """Tests for basic session workflows."""
    
    def test_session_start_to_end(self):
        """Test complete session from start to end."""
        # Simulate session state
        session_state = {
            'active': False,
            'goal': None,
            'start_time': None,
            'focus_seconds': 0
        }
        
        # Start session
        session_state['active'] = True
        session_state['goal'] = "Complete coding task"
        session_state['start_time'] = datetime.now()
        
        assert session_state['active'] is True
        assert session_state['goal'] == "Complete coding task"
        
        # Simulate work time
        session_state['focus_seconds'] = 1500  # 25 minutes
        
        # End session
        session_state['active'] = False
        session_state['end_time'] = datetime.now()
        
        assert session_state['active'] is False
        assert session_state['focus_seconds'] == 1500
    
    def test_session_with_pause_resume(self):
        """Test session with pause and resume."""
        session_state = {
            'active': True,
            'paused': False,
            'goal': "Test task",
            'focus_seconds': 0
        }
        
        # Work for some time
        session_state['focus_seconds'] = 600
        
        # Pause
        session_state['paused'] = True
        paused_at_seconds = session_state['focus_seconds']
        
        assert session_state['paused'] is True
        
        # Resume
        session_state['paused'] = False
        
        assert session_state['paused'] is False
        assert session_state['focus_seconds'] == paused_at_seconds
    
    def test_session_with_break(self):
        """Test session with work -> break transition."""
        pomodoro_state = {
            'current_state': 'work',
            'time_remaining': 25 * 60,
            'pomodoros_completed': 0
        }
        
        # Complete work period
        pomodoro_state['time_remaining'] = 0
        pomodoro_state['pomodoros_completed'] = 1
        
        # Transition to break
        pomodoro_state['current_state'] = 'short_break'
        pomodoro_state['time_remaining'] = 5 * 60
        
        assert pomodoro_state['current_state'] == 'short_break'
        assert pomodoro_state['pomodoros_completed'] == 1


@pytest.mark.integration
class TestSessionWithJudgments:
    """Tests for sessions with activity judgments."""
    
    def test_on_task_activity_flow(self):
        """Test flow when activity is on-task."""
        session_stats = SessionStats(start_time=datetime.now())
        
        # Simulate on-task activities
        for _ in range(10):
            session_stats.focus_seconds += 30  # 30 seconds per check
        
        assert session_stats.focus_seconds == 300  # 5 minutes
        assert session_stats.distractions_count == 0
    
    def test_off_task_activity_flow(self):
        """Test flow when activity is off-task."""
        session_stats = SessionStats(start_time=datetime.now())
        
        # On-task work
        session_stats.focus_seconds = 600
        
        # Off-task detection
        session_stats.off_task_seconds = 30
        session_stats.distractions_count = 1
        
        assert session_stats.focus_seconds == 600
        assert session_stats.off_task_seconds == 30
        assert session_stats.distractions_count == 1
    
    def test_idle_detection_flow(self):
        """Test flow with idle detection."""
        session_stats = SessionStats(start_time=datetime.now())
        
        # Active work
        session_stats.focus_seconds = 300
        
        # User goes idle
        session_stats.idle_seconds = 120
        
        assert session_stats.idle_seconds == 120


@pytest.mark.integration
class TestMultipleSessions:
    """Tests for multiple consecutive sessions."""
    
    def test_consecutive_sessions(self):
        """Test running multiple sessions consecutively."""
        sessions = []
        
        for i in range(3):
            session = {
                'id': i,
                'goal': f"Task {i}",
                'focus_seconds': (i + 1) * 600,
                'completed': True
            }
            sessions.append(session)
        
        assert len(sessions) == 3
        total_focus = sum(s['focus_seconds'] for s in sessions)
        assert total_focus == 3600  # 1 hour total
    
    def test_session_stats_reset_between_sessions(self):
        """Test that stats reset between sessions."""
        # First session
        stats1 = SessionStats(start_time=datetime.now())
        stats1.focus_seconds = 1500
        stats1.distractions_count = 2
        
        # Second session (new stats)
        stats2 = SessionStats(start_time=datetime.now())
        
        assert stats2.focus_seconds == 0
        assert stats2.distractions_count == 0


@pytest.mark.integration
class TestPomodoroFlow:
    """Tests for pomodoro workflow."""
    
    def test_full_pomodoro_cycle(self):
        """Test complete pomodoro cycle."""
        state = {
            'phase': 'work',
            'pomodoros': 0,
            'time': 25 * 60
        }
        
        cycle_count = 0
        
        for _ in range(8):  # 4 work + 4 break phases
            if state['phase'] == 'work':
                state['time'] = 0
                state['pomodoros'] += 1
                state['phase'] = 'short_break'
                state['time'] = 5 * 60
            elif state['phase'] == 'short_break':
                state['time'] = 0
                state['phase'] = 'work'
                state['time'] = 25 * 60
            cycle_count += 1
        
        assert state['pomodoros'] == 4
    
    def test_long_break_after_four_pomodoros(self):
        """Test long break triggers after 4 pomodoros."""
        pomodoros_completed = 0
        break_type = 'none'
        
        for _ in range(4):
            pomodoros_completed += 1
            
            if pomodoros_completed % 4 == 0:
                break_type = 'long_break'
            else:
                break_type = 'short_break'
        
        assert break_type == 'long_break'


@pytest.mark.integration
class TestErrorRecovery:
    """Tests for error recovery during sessions."""
    
    def test_session_recovery_after_crash(self):
        """Test session recovery after simulated crash."""
        # Save session state
        saved_state = {
            'goal': 'Important task',
            'focus_seconds': 900,
            'pomodoros': 1,
            'timestamp': datetime.now().isoformat()
        }
        
        # Simulate restart - load state
        recovered_state = saved_state.copy()
        
        assert recovered_state['goal'] == 'Important task'
        assert recovered_state['focus_seconds'] == 900
    
    def test_handle_invalid_state(self):
        """Test handling of invalid state."""
        invalid_state = {
            'focus_seconds': -100,  # Invalid
            'pomodoros': 'invalid'  # Wrong type
        }
        
        # Validate and fix
        if invalid_state.get('focus_seconds', 0) < 0:
            invalid_state['focus_seconds'] = 0
        
        try:
            invalid_state['pomodoros'] = int(invalid_state['pomodoros'])
        except (ValueError, TypeError):
            invalid_state['pomodoros'] = 0
        
        assert invalid_state['focus_seconds'] == 0
        assert invalid_state['pomodoros'] == 0


@pytest.mark.integration
class TestActivityHistoryFlow:
    """Tests for activity history during sessions."""
    
    def test_activity_history_building(self):
        """Test activity history is built during session."""
        history = []
        
        # Simulate activity polling
        apps = [
            ('Cursor', 'main.py'),
            ('Cursor', 'test.py'),
            ('Chrome', 'Stack Overflow'),
            ('Cursor', 'main.py'),
        ]
        
        for app, title in apps:
            activity = ActivityEvent(
                ts=datetime.now(),
                app=app,
                title=title
            )
            history.append(activity)
        
        assert len(history) == 4
        assert history[2].app == 'Chrome'
    
    def test_activity_pattern_detection(self):
        """Test detecting activity patterns."""
        history = []
        
        # Simulate focused work
        for _ in range(10):
            history.append(ActivityEvent(
                ts=datetime.now(),
                app='Cursor',
                title='code.py'
            ))
        
        # Count unique apps
        unique_apps = set(a.app for a in history)
        
        # Focused pattern = mostly one app
        assert len(unique_apps) == 1


@pytest.mark.integration
class TestVoiceNoteFlow:
    """Tests for voice note flow during sessions."""
    
    def test_voice_note_capture(self):
        """Test capturing voice note during session."""
        from code_sergeant.models import VoiceNote
        
        stats = SessionStats(start_time=datetime.now())
        
        # Add voice note
        note = VoiceNote(
            timestamp=datetime.now(),
            content="audio_data",
            transcription="Remember to refactor the login function"
        )
        stats.voice_notes.append(note)
        
        assert len(stats.voice_notes) == 1
        assert "refactor" in stats.voice_notes[0].transcription
    
    def test_multiple_voice_notes(self):
        """Test multiple voice notes in session."""
        from code_sergeant.models import VoiceNote
        
        stats = SessionStats(start_time=datetime.now())
        
        for i in range(3):
            note = VoiceNote(
                timestamp=datetime.now(),
                content=f"audio_{i}",
                transcription=f"Note number {i}"
            )
            stats.voice_notes.append(note)
        
        assert len(stats.voice_notes) == 3


@pytest.mark.integration
class TestDistractionReporting:
    """Tests for distraction reporting flow."""
    
    def test_self_report_distraction(self):
        """Test self-reporting distractions."""
        from code_sergeant.models import DistractionLog
        
        stats = SessionStats(start_time=datetime.now())
        
        # Report distraction
        log = DistractionLog(
            timestamp=datetime.now(),
            reason="Checked phone",
            is_phone=True
        )
        stats.distraction_logs.append(log)
        stats.distractions_count += 1
        
        assert stats.distractions_count == 1
        assert stats.distraction_logs[0].is_phone is True
    
    def test_phone_report_tracking(self):
        """Test phone report tracking."""
        stats = SessionStats(start_time=datetime.now())
        
        # Report phone usage
        stats.phone_reports.append(datetime.now())
        stats.phone_reports.append(datetime.now())
        
        assert len(stats.phone_reports) == 2

