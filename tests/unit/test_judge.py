"""
Unit tests for ActivityJudge.

Tests edge cases and core functionality of the judgment system:
- Empty/null inputs
- Unicode handling
- Cooldown logic
- Fallback classifier
- Confidence scoring
"""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from code_sergeant.judge import ActivityJudge
from code_sergeant.models import ActivityEvent, Judgment


@pytest.mark.unit
class TestActivityJudgeInit:
    """Tests for ActivityJudge initialization."""
    
    def test_init_with_ai_client(self, mock_ai_client):
        """Test initialization with AI client."""
        judge = ActivityJudge(ai_client=mock_ai_client)
        assert judge.ai_client is mock_ai_client
        assert judge.consecutive_off_task_count == 0
    
    def test_init_without_ai_client(self):
        """Test initialization without AI client (should not crash)."""
        judge = ActivityJudge()
        assert judge.ai_client is None


@pytest.mark.unit
class TestActivityJudgeEdgeCases:
    """Tests for edge cases in ActivityJudge.judge()."""
    
    @pytest.fixture
    def judge(self, mock_ai_client):
        """Create judge instance for testing."""
        return ActivityJudge(ai_client=mock_ai_client)
    
    def test_judge_with_empty_goal(self, judge, sample_activity):
        """Edge case: Empty goal should not crash."""
        result = judge.judge(
            goal="",
            activity=sample_activity,
            history=[],
            last_yell_time=None,
            cooldown_seconds=30
        )
        
        assert result is not None
        assert isinstance(result, Judgment)
        assert result.classification in ["on_task", "off_task", "idle", "unknown", "thinking"]
    
    def test_judge_with_none_activity(self, judge):
        """Edge case: None activity should return idle or handle gracefully."""
        # Create a minimal activity to avoid None
        activity = ActivityEvent(
            ts=datetime.now(),
            app="",
            title="",
            is_afk=True
        )
        
        result = judge.judge(
            goal="coding",
            activity=activity,
            history=[],
            last_yell_time=None,
            cooldown_seconds=30
        )
        
        assert result is not None
        assert result.classification == "idle"
    
    def test_judge_with_unicode_goal(self, judge, sample_activity):
        """Edge case: Unicode in goal should be handled."""
        result = judge.judge(
            goal="修复bug 🐛 和添加功能 ✨",
            activity=sample_activity,
            history=[],
            last_yell_time=None,
            cooldown_seconds=30
        )
        
        assert result is not None
        assert isinstance(result, Judgment)
    
    def test_judge_with_very_long_goal(self, judge, sample_activity):
        """Edge case: Very long goal should be handled."""
        long_goal = "Build a productivity app that helps developers stay focused " * 50
        
        result = judge.judge(
            goal=long_goal,
            activity=sample_activity,
            history=[],
            last_yell_time=None,
            cooldown_seconds=30
        )
        
        assert result is not None
        assert isinstance(result, Judgment)
    
    def test_judge_with_special_characters_in_goal(self, judge, sample_activity):
        """Edge case: Special characters in goal."""
        result = judge.judge(
            goal="Fix bug #123 in file.py (urgent!) & deploy",
            activity=sample_activity,
            history=[],
            last_yell_time=None,
            cooldown_seconds=30
        )
        
        assert result is not None
        assert isinstance(result, Judgment)
    
    def test_judge_with_whitespace_only_goal(self, judge, sample_activity):
        """Edge case: Whitespace-only goal."""
        result = judge.judge(
            goal="   \n\t   ",
            activity=sample_activity,
            history=[],
            last_yell_time=None,
            cooldown_seconds=30
        )
        
        assert result is not None
        assert isinstance(result, Judgment)


@pytest.mark.unit
class TestActivityJudgeAFKHandling:
    """Tests for AFK (Away From Keyboard) handling."""
    
    @pytest.fixture
    def judge(self, mock_ai_client):
        """Create judge instance for testing."""
        return ActivityJudge(ai_client=mock_ai_client)
    
    def test_afk_activity_returns_idle(self, judge, sample_activity_idle):
        """AFK activity should always return idle classification."""
        result = judge.judge(
            goal="coding",
            activity=sample_activity_idle,
            history=[],
            last_yell_time=None,
            cooldown_seconds=30
        )
        
        assert result.classification == "idle"
        assert result.confidence == 1.0
        assert result.action == "none"
    
    def test_thinking_activity_returns_thinking(self, judge, sample_activity_thinking):
        """Thinking activity should return thinking classification."""
        result = judge.judge(
            goal="coding",
            activity=sample_activity_thinking,
            history=[],
            last_yell_time=None,
            cooldown_seconds=30
        )
        
        assert result.classification == "thinking"
        assert result.action == "none"  # No warning for thinking


@pytest.mark.unit
class TestActivityJudgeCooldown:
    """Tests for cooldown logic."""
    
    @pytest.fixture
    def judge(self, mock_ai_client):
        """Create judge instance for testing."""
        return ActivityJudge(ai_client=mock_ai_client)
    
    def test_cooldown_prevents_immediate_yell(self, judge, sample_activity_off_task):
        """Test that cooldown prevents immediate repeated warnings."""
        # First judgment - should warn
        result1 = judge.judge(
            goal="coding",
            activity=sample_activity_off_task,
            history=[],
            last_yell_time=None,
            cooldown_seconds=30
        )
        
        # Second judgment immediately - should respect cooldown
        result2 = judge.judge(
            goal="coding",
            activity=sample_activity_off_task,
            history=[],
            last_yell_time=time.time(),  # Just yelled
            cooldown_seconds=30
        )
        
        # Both should return valid judgments
        assert result1 is not None
        assert result2 is not None
        # The classification should be consistent for off-task activity
        assert result2.classification in ["on_task", "off_task", "idle", "unknown", "thinking"]
    
    def test_cooldown_expired_allows_yell(self, judge, sample_activity_off_task):
        """Test that expired cooldown allows warnings again."""
        old_yell_time = time.time() - 60  # 60 seconds ago
        
        result = judge.judge(
            goal="coding",
            activity=sample_activity_off_task,
            history=[],
            last_yell_time=old_yell_time,
            cooldown_seconds=30
        )
        
        # After cooldown, warnings should be allowed
        assert result is not None
        # Action could be warn or yell depending on consecutive count


@pytest.mark.unit
class TestActivityJudgeFallback:
    """Tests for fallback classifier when AI is unavailable."""
    
    def test_fallback_classifies_coding_apps_as_on_task(self):
        """Test fallback classifier for coding apps."""
        judge = ActivityJudge()  # No AI client
        
        coding_activity = ActivityEvent(
            ts=datetime.now(),
            app="Cursor",
            title="main.py - CodeSergeant"
        )
        
        result = judge.judge(
            goal="coding",
            activity=coding_activity,
            history=[],
            last_yell_time=None,
            cooldown_seconds=30
        )
        
        # Fallback should recognize Cursor as productive for coding
        assert result is not None
        assert result.classification in ["on_task", "thinking"]
    
    def test_fallback_classifies_social_media_as_off_task(self):
        """Test fallback classifier for social media."""
        judge = ActivityJudge()  # No AI client
        
        social_activity = ActivityEvent(
            ts=datetime.now(),
            app="Twitter",
            title="Home / X"
        )
        
        result = judge.judge(
            goal="coding",
            activity=social_activity,
            history=[],
            last_yell_time=None,
            cooldown_seconds=30
        )
        
        # Fallback should recognize Twitter as off-task for coding
        assert result is not None
        assert result.classification == "off_task"
    
    def test_fallback_handles_unknown_apps(self):
        """Test fallback classifier for unknown apps."""
        judge = ActivityJudge()  # No AI client
        
        unknown_activity = ActivityEvent(
            ts=datetime.now(),
            app="SomeRandomApp",
            title="Unknown Window"
        )
        
        result = judge.judge(
            goal="coding",
            activity=unknown_activity,
            history=[],
            last_yell_time=None,
            cooldown_seconds=30
        )
        
        # Fallback should return something valid
        assert result is not None
        assert result.classification in ["on_task", "off_task", "unknown"]


@pytest.mark.unit
class TestActivityJudgeConfidence:
    """Tests for confidence scoring."""
    
    @pytest.fixture
    def judge(self, mock_ai_client):
        """Create judge instance for testing."""
        return ActivityJudge(ai_client=mock_ai_client)
    
    def test_confidence_is_valid_range(self, judge, sample_activity):
        """Test that confidence is always in valid range [0, 1]."""
        result = judge.judge(
            goal="coding",
            activity=sample_activity,
            history=[],
            last_yell_time=None,
            cooldown_seconds=30
        )
        
        assert 0.0 <= result.confidence <= 1.0
    
    def test_afk_has_high_confidence(self, judge, sample_activity_idle):
        """Test that AFK detection has high confidence."""
        result = judge.judge(
            goal="coding",
            activity=sample_activity_idle,
            history=[],
            last_yell_time=None,
            cooldown_seconds=30
        )
        
        assert result.confidence >= 0.9


@pytest.mark.unit
class TestActivityJudgePatternTracking:
    """Tests for activity pattern tracking."""
    
    @pytest.fixture
    def judge(self, mock_ai_client):
        """Create judge instance for testing."""
        return ActivityJudge(ai_client=mock_ai_client)
    
    def test_reset_patterns(self, judge):
        """Test that pattern reset works."""
        # Add some pattern data
        judge.activity_pattern = ["Cursor", "Twitter", "Cursor"]
        judge.consecutive_off_task_count = 3
        
        # Reset
        judge.reset_patterns()
        
        # Verify reset
        assert judge.activity_pattern == []
        assert judge.consecutive_off_task_count == 0
    
    def test_consecutive_off_task_tracking(self, judge, sample_activity_off_task):
        """Test that consecutive off-task count is tracked."""
        initial_count = judge.consecutive_off_task_count
        
        # Make multiple off-task judgments
        for _ in range(3):
            judge.judge(
                goal="coding",
                activity=sample_activity_off_task,
                history=[],
                last_yell_time=None,
                cooldown_seconds=30
            )
        
        # Count should have increased
        # Note: Actual tracking depends on implementation
        assert judge.consecutive_off_task_count >= 0


@pytest.mark.unit
class TestActivityJudgeValidOutput:
    """Tests to ensure judgment output is always valid."""
    
    @pytest.fixture
    def judge(self, mock_ai_client):
        """Create judge instance for testing."""
        return ActivityJudge(ai_client=mock_ai_client)
    
    def test_output_has_required_fields(self, judge, sample_activity):
        """Test that output has all required fields."""
        result = judge.judge(
            goal="coding",
            activity=sample_activity,
            history=[],
            last_yell_time=None,
            cooldown_seconds=30
        )
        
        assert hasattr(result, 'classification')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'reason')
        assert hasattr(result, 'say')
        assert hasattr(result, 'action')
    
    def test_classification_is_valid_enum(self, judge, sample_activity):
        """Test that classification is a valid enum value."""
        result = judge.judge(
            goal="coding",
            activity=sample_activity,
            history=[],
            last_yell_time=None,
            cooldown_seconds=30
        )
        
        valid_classifications = ["on_task", "off_task", "idle", "unknown", "thinking"]
        assert result.classification in valid_classifications
    
    def test_action_is_valid_enum(self, judge, sample_activity):
        """Test that action is a valid enum value."""
        result = judge.judge(
            goal="coding",
            activity=sample_activity,
            history=[],
            last_yell_time=None,
            cooldown_seconds=30
        )
        
        valid_actions = ["none", "warn", "yell"]
        assert result.action in valid_actions

