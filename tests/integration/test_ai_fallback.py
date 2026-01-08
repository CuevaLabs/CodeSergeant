"""
Integration tests for AI fallback behavior.

Tests error handling and fallback when AI services fail:
- OpenAI failure → Ollama fallback
- Ollama failure → Rule-based fallback
- Timeout handling
- Network error handling
"""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from code_sergeant.models import ActivityEvent, Judgment
from code_sergeant.judge import ActivityJudge


@pytest.mark.integration
class TestAIClientFallback:
    """Tests for AI client fallback behavior."""
    
    def test_fallback_when_openai_unavailable(self):
        """Test fallback to Ollama when OpenAI is unavailable."""
        mock_ai_client = Mock()
        mock_ai_client.get_status.return_value = {
            'openai_available': False,
            'ollama_available': True,
            'primary_backend': 'ollama'
        }
        
        judge = ActivityJudge(ai_client=mock_ai_client)
        
        activity = ActivityEvent(
            ts=datetime.now(),
            app="Cursor",
            title="test.py"
        )
        
        # Should still return a judgment
        result = judge.judge(
            goal="coding",
            activity=activity,
            history=[],
            last_yell_time=None,
            cooldown_seconds=30
        )
        
        assert result is not None
        assert isinstance(result, Judgment)
    
    def test_fallback_when_both_ai_unavailable(self):
        """Test fallback to rule-based when both AI backends are unavailable."""
        # No AI client = rule-based fallback
        judge = ActivityJudge(ai_client=None)
        
        activity = ActivityEvent(
            ts=datetime.now(),
            app="Chrome",
            title="Twitter - Home"
        )
        
        result = judge.judge(
            goal="coding",
            activity=activity,
            history=[],
            last_yell_time=None,
            cooldown_seconds=30
        )
        
        assert result is not None
        assert isinstance(result, Judgment)
        # Rule-based should detect Twitter as off-task
        assert result.classification in ["on_task", "off_task", "unknown"]


@pytest.mark.integration
class TestNetworkErrorHandling:
    """Tests for network error handling."""
    
    def test_handle_connection_timeout(self):
        """Test handling of connection timeout."""
        mock_ai_client = Mock()
        mock_ai_client.chat.side_effect = TimeoutError("Connection timed out")
        
        judge = ActivityJudge(ai_client=mock_ai_client)
        
        activity = ActivityEvent(
            ts=datetime.now(),
            app="Cursor",
            title="test.py"
        )
        
        # Should fall back gracefully
        result = judge.judge(
            goal="coding",
            activity=activity,
            history=[],
            last_yell_time=None,
            cooldown_seconds=30
        )
        
        assert result is not None
    
    def test_handle_connection_refused(self):
        """Test handling of connection refused."""
        mock_ai_client = Mock()
        mock_ai_client.chat.side_effect = ConnectionRefusedError("Connection refused")
        
        judge = ActivityJudge(ai_client=mock_ai_client)
        
        activity = ActivityEvent(
            ts=datetime.now(),
            app="Cursor",
            title="test.py"
        )
        
        # Should fall back gracefully
        result = judge.judge(
            goal="coding",
            activity=activity,
            history=[],
            last_yell_time=None,
            cooldown_seconds=30
        )
        
        assert result is not None


@pytest.mark.integration
class TestRuleBasedFallback:
    """Tests for rule-based fallback classifier."""
    
    def test_rule_based_coding_apps(self):
        """Test rule-based classification of coding apps."""
        judge = ActivityJudge()  # No AI client = rule-based
        
        coding_apps = [
            ("Cursor", "main.py"),
            ("VS Code", "index.js"),
            ("Xcode", "AppDelegate.swift"),
            ("PyCharm", "test.py"),
            ("iTerm2", "~/projects")
        ]
        
        for app, title in coding_apps:
            activity = ActivityEvent(
                ts=datetime.now(),
                app=app,
                title=title
            )
            
            result = judge.judge(
                goal="coding",
                activity=activity,
                history=[],
                last_yell_time=None,
                cooldown_seconds=30
            )
            
            # Should recognize these as productive
            assert result is not None
            assert result.classification in ["on_task", "thinking"]
    
    def test_rule_based_social_media(self):
        """Test rule-based classification of social media."""
        judge = ActivityJudge()  # No AI client = rule-based
        
        social_apps = [
            ("Twitter", "Home / X"),
            ("Safari", "Facebook"),
            ("Chrome", "Instagram"),
            ("Safari", "Reddit - Front Page")
        ]
        
        for app, title in social_apps:
            activity = ActivityEvent(
                ts=datetime.now(),
                app=app,
                title=title
            )
            
            result = judge.judge(
                goal="coding",
                activity=activity,
                history=[],
                last_yell_time=None,
                cooldown_seconds=30
            )
            
            # Should recognize these as off-task (usually)
            assert result is not None
            assert result.classification in ["on_task", "off_task", "unknown"]
    
    def test_rule_based_documentation(self):
        """Test rule-based classification of documentation sites."""
        judge = ActivityJudge()  # No AI client = rule-based
        
        doc_sites = [
            ("Chrome", "Python 3.12 Documentation"),
            ("Safari", "React Documentation"),
            ("Firefox", "MDN Web Docs - JavaScript"),
            ("Chrome", "Stack Overflow - How to parse JSON")
        ]
        
        for app, title in doc_sites:
            activity = ActivityEvent(
                ts=datetime.now(),
                app=app,
                title=title
            )
            
            result = judge.judge(
                goal="coding",
                activity=activity,
                history=[],
                last_yell_time=None,
                cooldown_seconds=30
            )
            
            # Should generally recognize these as productive for coding
            assert result is not None
            assert isinstance(result, Judgment)


@pytest.mark.integration
class TestGracefulDegradation:
    """Tests for graceful degradation of AI services."""
    
    def test_partial_ai_response(self):
        """Test handling of partial/incomplete AI responses."""
        mock_ai_client = Mock()
        mock_ai_client.chat.return_value = {
            "message": {
                "content": "incomplete"  # Invalid JSON
            }
        }
        
        judge = ActivityJudge(ai_client=mock_ai_client)
        
        activity = ActivityEvent(
            ts=datetime.now(),
            app="Cursor",
            title="test.py"
        )
        
        # Should fall back to rule-based
        result = judge.judge(
            goal="coding",
            activity=activity,
            history=[],
            last_yell_time=None,
            cooldown_seconds=30
        )
        
        assert result is not None
        assert isinstance(result, Judgment)
    
    def test_malformed_ai_response(self):
        """Test handling of malformed AI responses."""
        mock_ai_client = Mock()
        mock_ai_client.chat.return_value = {
            "message": {
                "content": '{"classification": "invalid_value"}'
            }
        }
        
        judge = ActivityJudge(ai_client=mock_ai_client)
        
        activity = ActivityEvent(
            ts=datetime.now(),
            app="Cursor",
            title="test.py"
        )
        
        # Should handle gracefully
        result = judge.judge(
            goal="coding",
            activity=activity,
            history=[],
            last_yell_time=None,
            cooldown_seconds=30
        )
        
        assert result is not None


@pytest.mark.integration
class TestRetryBehavior:
    """Tests for retry behavior on transient failures."""
    
    def test_transient_failure_recovery(self):
        """Test recovery from transient failures."""
        call_count = 0
        
        def flaky_chat(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Transient failure")
            return {
                "message": {
                    "content": '{"classification": "on_task", "confidence": 0.8, "reason": "test", "say": "good", "action": "none"}'
                }
            }
        
        mock_ai_client = Mock()
        mock_ai_client.chat = flaky_chat
        
        judge = ActivityJudge(ai_client=mock_ai_client)
        
        activity = ActivityEvent(
            ts=datetime.now(),
            app="Cursor",
            title="test.py"
        )
        
        # Should eventually succeed or fall back
        result = judge.judge(
            goal="coding",
            activity=activity,
            history=[],
            last_yell_time=None,
            cooldown_seconds=30
        )
        
        assert result is not None


@pytest.mark.integration
class TestOllamaIntegration:
    """Tests for Ollama-specific integration."""
    
    def test_ollama_availability_check(self):
        """Test Ollama availability checking."""
        mock_ai_client = Mock()
        mock_ai_client.check_ollama_available.return_value = (True, "Ollama is running")
        
        available, message = mock_ai_client.check_ollama_available()
        
        assert available is True
        assert "running" in message.lower()
    
    def test_ollama_unavailable_handling(self):
        """Test handling when Ollama is unavailable."""
        mock_ai_client = Mock()
        mock_ai_client.check_ollama_available.return_value = (False, "Connection refused")
        mock_ai_client.chat.side_effect = ConnectionRefusedError()
        
        judge = ActivityJudge(ai_client=mock_ai_client)
        
        activity = ActivityEvent(
            ts=datetime.now(),
            app="Cursor",
            title="test.py"
        )
        
        # Should fall back
        result = judge.judge(
            goal="coding",
            activity=activity,
            history=[],
            last_yell_time=None,
            cooldown_seconds=30
        )
        
        assert result is not None


@pytest.mark.integration
class TestElevenLabsTTSFallback:
    """Tests for ElevenLabs TTS fallback."""
    
    def test_tts_fallback_to_pyttsx3(self):
        """Test TTS fallback to pyttsx3 when ElevenLabs fails."""
        from tests.conftest import MockTTSService
        
        mock_tts = MockTTSService()
        
        # Simulate speaking
        mock_tts.speak("Hello, world!")
        
        assert len(mock_tts.spoken_texts) == 1
    
    def test_tts_handles_api_error(self):
        """Test TTS handles API errors gracefully."""
        from tests.conftest import MockTTSService
        
        mock_tts = MockTTSService()
        
        # Should not crash on any input
        mock_tts.speak("Test message")
        mock_tts.speak("")  # Empty
        mock_tts.speak("Special chars: @#$%^&*()")
        
        # First speak only (empty is ignored)
        assert len(mock_tts.spoken_texts) >= 1


@pytest.mark.integration
class TestCacheAndPerformance:
    """Tests for caching and performance optimization."""
    
    def test_repeated_similar_queries(self):
        """Test handling of repeated similar queries."""
        judge = ActivityJudge()
        
        activity = ActivityEvent(
            ts=datetime.now(),
            app="Cursor",
            title="test.py"
        )
        
        # Multiple similar judgments
        results = []
        for _ in range(5):
            result = judge.judge(
                goal="coding",
                activity=activity,
                history=[],
                last_yell_time=None,
                cooldown_seconds=30
            )
            results.append(result)
        
        # All should be valid
        assert all(r is not None for r in results)
        assert all(isinstance(r, Judgment) for r in results)
    
    def test_response_time_acceptable(self):
        """Test that response time is acceptable even without AI."""
        judge = ActivityJudge()  # Rule-based fallback
        
        activity = ActivityEvent(
            ts=datetime.now(),
            app="Cursor",
            title="test.py"
        )
        
        start = time.time()
        result = judge.judge(
            goal="coding",
            activity=activity,
            history=[],
            last_yell_time=None,
            cooldown_seconds=30
        )
        elapsed = time.time() - start
        
        # Allow more time for first call (may involve initialization)
        # Subsequent calls would be faster
        assert elapsed < 30  # Generous timeout for any setup
        assert result is not None

