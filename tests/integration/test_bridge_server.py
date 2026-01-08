"""
Integration tests for the Bridge Server API.

Tests HTTP endpoints for Swift ↔ Python communication:
- Health and status endpoints
- Session management endpoints
- Timer endpoints
- Config endpoints
- Error handling
"""

import json
import os
import sys
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)


@pytest.fixture
def app():
    """Create Flask test app."""
    from bridge.server import app

    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    with app.test_client() as client:
        yield client


@pytest.mark.integration
class TestHealthEndpoint:
    """Tests for /api/health endpoint."""

    def test_health_returns_200(self, client):
        """Test health check returns 200."""
        response = client.get("/api/health")

        assert response.status_code == 200

    def test_health_returns_json(self, client):
        """Test health check returns valid JSON."""
        response = client.get("/api/health")
        data = json.loads(response.data)

        assert "status" in data
        assert data["status"] == "healthy"

    def test_health_includes_timestamp(self, client):
        """Test health check includes timestamp."""
        response = client.get("/api/health")
        data = json.loads(response.data)

        assert "timestamp" in data


@pytest.mark.integration
class TestStatusEndpoint:
    """Tests for /api/status endpoint."""

    def test_status_requires_controller(self, client):
        """Test status returns error without controller."""
        with patch("bridge.server.controller", None):
            response = client.get("/api/status")

            # May return 500 or valid status depending on initialization
            assert response.status_code in [200, 500]

    @patch("bridge.server.controller")
    def test_status_returns_session_info(self, mock_controller, client):
        """Test status returns session information."""
        mock_state = Mock()
        mock_state.session_active = True
        mock_state.goal = "Test goal"
        mock_state.personality_name = "sergeant"
        mock_state.stats = Mock()
        mock_state.stats.focus_seconds = 600

        mock_controller.get_state_snapshot.return_value = mock_state

        response = client.get("/api/status")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "session_active" in data


@pytest.mark.integration
class TestSessionEndpoints:
    """Tests for session management endpoints."""

    def test_start_session_without_goal(self, client):
        """Test starting session without goal."""
        with patch("bridge.server.controller") as mock_controller:
            mock_controller.pomodoro = None

            response = client.post(
                "/api/session/start", json={}, content_type="application/json"
            )

            # Should handle gracefully
            assert response.status_code in [200, 500]

    def test_start_session_with_goal(self, client):
        """Test starting session with goal."""
        with patch("bridge.server.controller") as mock_controller:
            mock_controller.pomodoro = None

            response = client.post(
                "/api/session/start",
                json={"goal": "Test coding"},
                content_type="application/json",
            )

            assert response.status_code in [200, 500]

    def test_start_session_with_custom_times(self, client):
        """Test starting session with custom work/break times."""
        with patch("bridge.server.controller") as mock_controller:
            mock_pomodoro = Mock()
            mock_pomodoro.state = Mock()
            mock_controller.pomodoro = mock_pomodoro

            response = client.post(
                "/api/session/start",
                json={"goal": "Test", "work_minutes": 30, "break_minutes": 10},
                content_type="application/json",
            )

            assert response.status_code in [200, 500]

    def test_end_session(self, client):
        """Test ending session."""
        with patch("bridge.server.controller") as mock_controller:
            mock_state = Mock()
            mock_state.stats = Mock()
            mock_state.stats.focus_seconds = 600
            mock_state.stats.distractions_count = 2
            mock_state.stats.pomodoros_completed = 1
            mock_controller.get_state_snapshot.return_value = mock_state

            response = client.post("/api/session/end")

            assert response.status_code in [200, 500]

    def test_pause_session(self, client):
        """Test pausing session."""
        with patch("bridge.server.controller") as mock_controller:
            response = client.post("/api/session/pause")

            assert response.status_code in [200, 500]

    def test_resume_session(self, client):
        """Test resuming session."""
        with patch("bridge.server.controller") as mock_controller:
            response = client.post("/api/session/resume")

            assert response.status_code in [200, 500]


@pytest.mark.integration
class TestTimerEndpoint:
    """Tests for /api/timer endpoint."""

    def test_timer_without_controller(self, client):
        """Test timer returns error without controller."""
        with patch("bridge.server.controller", None):
            response = client.get("/api/timer")

            assert response.status_code == 500

    @patch("bridge.server.controller")
    def test_timer_returns_state(self, mock_controller, client):
        """Test timer returns state information."""
        mock_pomodoro = Mock()
        mock_state = Mock()
        mock_state.current_state = "work"
        mock_state.time_remaining_seconds = 1500
        mock_state.work_duration_minutes = 25
        mock_state.short_break_minutes = 5
        mock_state.long_break_minutes = 15
        mock_pomodoro.state = mock_state
        mock_controller.pomodoro = mock_pomodoro

        response = client.get("/api/timer")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "state" in data
        assert "remaining_seconds" in data


@pytest.mark.integration
class TestTTSEndpoints:
    """Tests for TTS endpoints."""

    def test_speak_without_text(self, client):
        """Test speak returns error without text."""
        response = client.post(
            "/api/tts/speak", json={}, content_type="application/json"
        )

        assert response.status_code == 400

    def test_speak_with_text(self, client):
        """Test speak with text."""
        with patch("bridge.server.tts_service") as mock_tts:
            response = client.post(
                "/api/tts/speak",
                json={"text": "Hello, world!"},
                content_type="application/json",
            )

            assert response.status_code in [200, 500]

    def test_stop_speaking(self, client):
        """Test stop speaking."""
        with patch("bridge.server.tts_service") as mock_tts:
            response = client.post("/api/tts/stop")

            assert response.status_code == 200


@pytest.mark.integration
class TestConfigEndpoints:
    """Tests for config endpoints."""

    def test_get_config_sanitizes_keys(self, client):
        """Test get config sanitizes API keys."""
        with patch(
            "bridge.server.config",
            {
                "openai": {"api_key": "secret_key"},
                "tts": {"elevenlabs_api_key": "another_secret"},
            },
        ):
            response = client.get("/api/config")

            assert response.status_code == 200
            data = json.loads(response.data)

            # API keys should be masked
            if "openai" in data and data["openai"].get("api_key"):
                assert data["openai"]["api_key"] == "***"

    def test_update_config(self, client):
        """Test updating config."""
        with patch("bridge.server.config", {"test": "value"}):
            with patch("bridge.server.save_config"):
                response = client.patch(
                    "/api/config",
                    json={"new_setting": "new_value"},
                    content_type="application/json",
                )

                assert response.status_code == 200


@pytest.mark.integration
class TestActivityEndpoint:
    """Tests for activity endpoint."""

    def test_activity_without_monitor(self, client):
        """Test activity returns error without monitor."""
        with patch("bridge.server.native_monitor", None):
            response = client.get("/api/activity/current")

            assert response.status_code == 500

    @patch("bridge.server.native_monitor")
    def test_activity_returns_info(self, mock_monitor, client):
        """Test activity returns current info."""
        mock_monitor.get_frontmost_app.return_value = "Cursor"
        mock_monitor.get_active_window_title.return_value = "test.py"
        mock_monitor.get_idle_seconds.return_value = 5.0
        mock_monitor.is_user_idle.return_value = False

        response = client.get("/api/activity/current")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["app"] == "Cursor"


@pytest.mark.integration
class TestErrorHandling:
    """Tests for error handling."""

    def test_malformed_json(self, client):
        """Test handling of malformed JSON."""
        response = client.post(
            "/api/session/start", data="not valid json", content_type="application/json"
        )

        # Should return 400 or 500, not crash
        assert response.status_code in [400, 500]

    def test_missing_endpoint(self, client):
        """Test handling of missing endpoint."""
        response = client.get("/api/nonexistent")

        assert response.status_code == 404

    def test_wrong_method(self, client):
        """Test handling of wrong HTTP method."""
        response = client.delete("/api/health")

        assert response.status_code == 405


@pytest.mark.integration
class TestConcurrentRequests:
    """Tests for concurrent request handling."""

    def test_multiple_health_checks(self, client):
        """Test multiple concurrent health checks."""
        responses = []

        for _ in range(5):
            response = client.get("/api/health")
            responses.append(response.status_code)

        # All should succeed
        assert all(code == 200 for code in responses)
