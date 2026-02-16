"""Tests for the local Flask server."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from zepp_export.server import create_app, _read_cache, _write_cache, CACHE_DIR


@pytest.fixture
def mock_client():
    """Create a mock ZeppClient."""
    client = MagicMock()

    client.get_heart_rate.return_value = [
        {"minute": 360, "time": "06:00", "bpm": 62},
        {"minute": 361, "time": "06:01", "bpm": 64},
        {"minute": 720, "time": "12:00", "bpm": 78},
    ]

    client.get_sleep.return_value = {
        "date": "2026-02-06",
        "resting_hr": 55,
        "sleep_score": 82,
        "deep_minutes": 95,
        "light_minutes": 180,
        "duration_minutes": 420,
        "stages": [
            {"start_minute": 1400, "end_minute": 1430, "duration_minutes": 30, "stage": "light"},
            {"start_minute": 1430, "end_minute": 1500, "duration_minutes": 70, "stage": "deep"},
        ],
    }

    client.get_steps.return_value = {
        "date": "2026-02-06",
        "total_steps": 8500,
        "distance_meters": 6200,
        "calories": 320,
        "goal": 8000,
    }

    client.get_stress.return_value = [{
        "timestamp": 1738800000000,
        "avg_stress": 35,
        "max_stress": 72,
        "min_stress": 12,
        "zone_percentages": {"relaxed": 40, "normal": 35, "medium": 20, "high": 5},
        "readings": [{"time": "06:00", "value": 28}, {"time": "06:05", "value": 32}],
    }]

    client.get_training_load.return_value = [{
        "timestamp": 1738800000000,
        "atl": 45.2,
        "ctl": 38.1,
        "tsb": -7.1,
        "exercise_score": 120,
    }]

    client.get_sport_load.return_value = [{
        "date": "2026-02-06",
        "daily_load": 85,
        "weekly_load": 420,
        "optimal_min": 300,
        "optimal_max": 600,
    }]

    return client


@pytest.fixture
def _clean_cache(tmp_path):
    """Patch CACHE_DIR to a temp directory so tests never hit real cache."""
    with patch("zepp_export.server.CACHE_DIR", tmp_path):
        yield tmp_path


@pytest.fixture
def app(mock_client, _clean_cache):
    """Create the Flask test app with a clean cache."""
    application = create_app(mock_client)
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app):
    """Create a Flask test client."""
    return app.test_client()


class TestAPIEndpoints:
    """Test that all API endpoints return correct data."""

    def test_heart_rate(self, client, mock_client):
        resp = client.get("/api/heart-rate/2026-02-06")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 3
        assert data[0]["bpm"] == 62
        mock_client.get_heart_rate.assert_called_once_with("2026-02-06")

    def test_sleep(self, client, mock_client):
        resp = client.get("/api/sleep/2026-02-06")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["sleep_score"] == 82
        assert data["resting_hr"] == 55
        mock_client.get_sleep.assert_called_once_with("2026-02-06")

    def test_steps(self, client, mock_client):
        resp = client.get("/api/steps/2026-02-06")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total_steps"] == 8500
        mock_client.get_steps.assert_called_once_with("2026-02-06")

    def test_stress(self, client, mock_client):
        resp = client.get("/api/stress/2026-02-06")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["avg_stress"] == 35
        mock_client.get_stress.assert_called_once_with("2026-02-06", "2026-02-06")

    def test_training_load(self, client, mock_client):
        resp = client.get("/api/training-load")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["atl"] == 45.2

    def test_sport_load(self, client, mock_client):
        resp = client.get("/api/sport-load")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["daily_load"] == 85

    def test_summary(self, client, mock_client):
        resp = client.get("/api/summary/2026-02-06")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["heart_rate"]["avg"] == 68
        assert data["heart_rate"]["min"] == 62
        assert data["heart_rate"]["max"] == 78
        assert data["sleep"]["sleep_score"] == 82
        assert data["steps"]["total_steps"] == 8500
        assert data["stress"]["avg"] == 35


class TestCaching:
    """Test that the file-based cache works correctly."""

    def test_cache_write_and_read(self, tmp_path):
        with patch("zepp_export.server.CACHE_DIR", tmp_path):
            _write_cache("heart-rate", "2026-02-06", [{"bpm": 72}])
            result = _read_cache("heart-rate", "2026-02-06")
            assert result == [{"bpm": 72}]

    def test_cache_miss(self, tmp_path):
        with patch("zepp_export.server.CACHE_DIR", tmp_path):
            result = _read_cache("heart-rate", "2026-01-01")
            assert result is None

    def test_cached_response_skips_api(self, client, mock_client, tmp_path):
        with patch("zepp_export.server.CACHE_DIR", tmp_path):
            # First call hits the API
            resp1 = client.get("/api/heart-rate/2026-02-06")
            assert resp1.status_code == 200
            assert mock_client.get_heart_rate.call_count == 1

            # Second call should use cache
            resp2 = client.get("/api/heart-rate/2026-02-06")
            assert resp2.status_code == 200
            assert mock_client.get_heart_rate.call_count == 1  # still 1


class TestDashboard:
    """Test that the dashboard page is served."""

    def test_index_serves_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"zepp-export" in resp.data


class TestErrorHandling:
    """Test error responses from the API."""

    def test_api_error_returns_500(self, tmp_path):
        from zepp_export.exceptions import ZeppAPIError

        mock_client = MagicMock()
        mock_client.get_heart_rate.side_effect = ZeppAPIError("Server error")
        test_app = create_app(mock_client)
        test_app.config["TESTING"] = True

        with patch("zepp_export.server.CACHE_DIR", tmp_path):
            with test_app.test_client() as c:
                resp = c.get("/api/heart-rate/2026-02-06")
                assert resp.status_code == 500
                data = resp.get_json()
                assert "error" in data
