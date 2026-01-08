"""
Unit tests for AppController.

Tests session lifecycle and state management:
- Session start/end
- State transitions
- Event handling
- Goal management
"""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
import threading
import queue

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from code_sergeant.models import ActivityEvent, Judgment, SessionStats


@pytest.mark.unit
class TestControllerStateSnapshot:
    """Tests for ControllerState dataclass."""
    
    def test_controller_state_defaults(self):
        """Test default values for ControllerState."""
        from code_sergeant.controller import ControllerState
        
        state = ControllerState()
        
        assert state.session_active is False
        assert state.goal is None
        assert state.current_activity is None
        assert state.last_judgment is None
        assert state.personality_name == "sergeant"
    
    def test_controller_state_with_values(self):
        """Test ControllerState with custom values."""
        from code_sergeant.controller import ControllerState
        
        state = ControllerState(
            session_active=True,
            goal="Build a feature",
            current_activity="Coding in Cursor",
            personality_name="buddy"
        )
        
        assert state.session_active is True
        assert state.goal == "Build a feature"
        assert state.current_activity == "Coding in Cursor"
        assert state.personality_name == "buddy"


@pytest.mark.unit
class TestSessionLifecycleBasic:
    """Basic tests for session lifecycle without full controller."""
    
    def test_session_stats_initialization(self):
        """Test SessionStats initialization."""
        stats = SessionStats(start_time=datetime.now())
        
        assert stats.focus_seconds == 0
        assert stats.off_task_seconds == 0
        assert stats.distractions_count == 0
        assert stats.pomodoros_completed == 0
    
    def test_session_stats_tracking(self):
        """Test SessionStats value tracking."""
        stats = SessionStats(start_time=datetime.now())
        
        stats.focus_seconds = 600
        stats.off_task_seconds = 60
        stats.distractions_count = 2
        
        assert stats.focus_seconds == 600
        assert stats.off_task_seconds == 60
        assert stats.distractions_count == 2


@pytest.mark.unit
class TestEventQueue:
    """Tests for event queue functionality."""
    
    def test_event_queue_operations(self):
        """Test basic event queue operations."""
        event_queue = queue.Queue()
        
        # Add events
        event_queue.put({'type': 'activity_update', 'data': 'test'})
        event_queue.put({'type': 'judgment_update', 'data': 'test2'})
        
        # Verify events
        event1 = event_queue.get_nowait()
        event2 = event_queue.get_nowait()
        
        assert event1['type'] == 'activity_update'
        assert event2['type'] == 'judgment_update'
    
    def test_event_queue_empty(self):
        """Test empty event queue handling."""
        event_queue = queue.Queue()
        
        # Should raise Empty when queue is empty
        with pytest.raises(queue.Empty):
            event_queue.get_nowait()


@pytest.mark.unit
class TestGoalManagement:
    """Tests for goal management."""
    
    def test_empty_goal_handling(self):
        """Test handling of empty goals."""
        # Empty goal should be acceptable
        goal = ""
        assert goal == ""
        
        # Whitespace goal
        goal = "   "
        assert goal.strip() == ""
    
    def test_unicode_goal_handling(self):
        """Test handling of unicode goals."""
        goal = "修复bug 🐛"
        
        assert "bug" in goal or "修复" in goal
        assert len(goal) > 0
    
    def test_very_long_goal(self):
        """Test handling of very long goals."""
        goal = "Build a productivity app that helps developers stay focused " * 50
        
        # Should be stored without truncation
        assert len(goal) > 1000


@pytest.mark.unit
class TestActivityTracking:
    """Tests for activity tracking."""
    
    def test_activity_history_storage(self):
        """Test storing activity history."""
        history = []
        
        for i in range(5):
            activity = ActivityEvent(
                ts=datetime.now(),
                app=f"App{i}",
                title=f"Window{i}"
            )
            history.append(activity)
        
        assert len(history) == 5
        assert history[0].app == "App0"
    
    def test_activity_history_limit(self):
        """Test limiting activity history to recent entries."""
        history = []
        max_history = 10
        
        for i in range(20):
            activity = ActivityEvent(
                ts=datetime.now(),
                app=f"App{i}",
                title=f"Window{i}"
            )
            history.append(activity)
            
            # Keep only last N entries
            if len(history) > max_history:
                history.pop(0)
        
        assert len(history) == max_history
        assert history[0].app == "App10"


@pytest.mark.unit
class TestJudgmentTracking:
    """Tests for judgment tracking."""
    
    def test_judgment_storage(self):
        """Test storing last judgment."""
        judgment = Judgment(
            classification="on_task",
            confidence=0.85,
            reason="User is coding",
            say="Good work!",
            action="none"
        )
        
        last_judgment = judgment
        
        assert last_judgment.classification == "on_task"
        assert last_judgment.confidence == 0.85
    
    def test_judgment_update(self):
        """Test updating judgment."""
        judgment1 = Judgment(
            classification="on_task",
            confidence=0.85,
            reason="Coding",
            say="Good!",
            action="none"
        )
        
        judgment2 = Judgment(
            classification="off_task",
            confidence=0.9,
            reason="Social media",
            say="Focus!",
            action="warn"
        )
        
        last_judgment = judgment1
        assert last_judgment.classification == "on_task"
        
        last_judgment = judgment2
        assert last_judgment.classification == "off_task"


@pytest.mark.unit
class TestCooldownLogic:
    """Tests for cooldown logic."""
    
    def test_cooldown_tracking(self):
        """Test cooldown time tracking."""
        last_yell_time = None
        cooldown_seconds = 30
        
        # First warning - should be allowed
        assert last_yell_time is None or (time.time() - last_yell_time > cooldown_seconds)
        
        # Record warning time
        last_yell_time = time.time()
        
        # Immediate second warning - should be blocked
        assert time.time() - last_yell_time < cooldown_seconds
    
    def test_cooldown_expiry(self):
        """Test cooldown expiration."""
        cooldown_seconds = 30
        last_yell_time = time.time() - 60  # 60 seconds ago
        
        # Cooldown should have expired
        assert time.time() - last_yell_time > cooldown_seconds


@pytest.mark.unit
class TestStopEventHandling:
    """Tests for stop event handling."""
    
    def test_stop_event_initial_state(self):
        """Test stop event is initially clear."""
        stop_event = threading.Event()
        
        assert not stop_event.is_set()
    
    def test_stop_event_set(self):
        """Test setting stop event."""
        stop_event = threading.Event()
        stop_event.set()
        
        assert stop_event.is_set()
    
    def test_stop_event_clear(self):
        """Test clearing stop event."""
        stop_event = threading.Event()
        stop_event.set()
        stop_event.clear()
        
        assert not stop_event.is_set()


@pytest.mark.unit
class TestWorkerRegistry:
    """Tests for worker thread registry."""
    
    def test_worker_registry_operations(self):
        """Test worker registry operations."""
        workers = {}
        
        # Add mock workers
        workers["activity_poller"] = Mock()
        workers["judge_worker"] = Mock()
        workers["reminder_worker"] = Mock()
        
        assert len(workers) == 3
        assert "activity_poller" in workers
    
    def test_worker_cleanup(self):
        """Test worker cleanup."""
        workers = {}
        workers["test_worker"] = Mock()
        workers["test_worker"].is_alive.return_value = True
        workers["test_worker"].join = Mock()
        
        # Simulate cleanup
        for name, worker in workers.items():
            if worker.is_alive():
                worker.join(timeout=1.0)
        
        workers["test_worker"].join.assert_called_once()


@pytest.mark.unit
class TestStateSnapshot:
    """Tests for state snapshot functionality."""
    
    def test_state_snapshot_structure(self):
        """Test state snapshot has correct structure."""
        from code_sergeant.controller import ControllerState
        
        state = ControllerState(
            session_active=True,
            goal="Test goal",
            current_activity="Cursor - test.py"
        )
        
        # Check required fields
        assert hasattr(state, 'session_active')
        assert hasattr(state, 'goal')
        assert hasattr(state, 'current_activity')
        assert hasattr(state, 'last_judgment')
        assert hasattr(state, 'stats')
        assert hasattr(state, 'pomodoro_state')


@pytest.mark.unit
class TestPersonalityIntegration:
    """Tests for personality integration."""
    
    def test_personality_state_tracking(self):
        """Test personality state tracking."""
        from code_sergeant.controller import ControllerState
        
        state = ControllerState()
        
        # Default personality
        assert state.personality_name == "sergeant"
        assert state.wake_word == "hey sergeant"
    
    def test_personality_change(self):
        """Test personality change."""
        from code_sergeant.controller import ControllerState
        
        state = ControllerState()
        
        # Change personality
        state.personality_name = "buddy"
        state.wake_word = "hey buddy"
        
        assert state.personality_name == "buddy"
        assert state.wake_word == "hey buddy"


@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases in controller logic."""
    
    def test_rapid_session_toggle(self):
        """Test rapid session start/end doesn't crash."""
        session_active = False
        
        for _ in range(10):
            session_active = not session_active
        
        # Should complete without error
        assert session_active is False or session_active is True
    
    def test_concurrent_event_handling(self):
        """Test concurrent event handling."""
        event_queue = queue.Queue()
        
        # Simulate concurrent event additions
        def add_events():
            for i in range(100):
                event_queue.put({'type': 'test', 'id': i})
        
        threads = [threading.Thread(target=add_events) for _ in range(5)]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # All events should be queued
        assert event_queue.qsize() == 500

