"""Local Flask server for zepp-export.

Serves health data as clean REST endpoints with a file-based cache.
Data is cached in ~/.zepp-export/data/ as dated JSON files so it
persists across restarts and is human-inspectable.

Run with: python -m zepp_export serve --port 8080
"""

import json
import os
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, send_from_directory

from .client import ZeppClient
from .exceptions import ZeppAuthError, ZeppAPIError

CACHE_DIR = Path.home() / ".zepp-export" / "data"


def _cache_path(data_type: str, key: str) -> Path:
    """Get the cache file path for a data type and key (usually a date)."""
    d = CACHE_DIR / data_type
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{key}.json"


def _read_cache(data_type: str, key: str):
    """Read cached data. Returns None on miss."""
    path = _cache_path(data_type, key)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def _write_cache(data_type: str, key: str, data):
    """Write data to the cache."""
    path = _cache_path(data_type, key)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def _is_today(date_str: str) -> bool:
    """Check if a date string is today. Today's data shouldn't be cached."""
    return date_str == datetime.now().strftime("%Y-%m-%d")


def _is_empty(data) -> bool:
    """Check if API data is empty / has no meaningful content."""
    if data is None:
        return True
    if isinstance(data, list) and len(data) == 0:
        return True
    if isinstance(data, dict) and len(data) == 0:
        return True
    return False


def create_app(client: ZeppClient) -> Flask:
    """Create and configure the Flask app.

    Args:
        client: An authenticated ZeppClient instance.

    Returns:
        Configured Flask app.
    """
    dashboard_dir = os.path.join(os.path.dirname(__file__), "dashboard")
    static_dir = os.path.join(dashboard_dir, "static")

    app = Flask(__name__, static_folder=static_dir)

    # ------------------------------------------------------------------
    # Dashboard routes
    # ------------------------------------------------------------------

    @app.route("/")
    def index():
        return send_from_directory(dashboard_dir, "index.html")

    @app.route("/static/<path:filename>")
    def serve_static(filename):
        return send_from_directory(static_dir, filename)

    # ------------------------------------------------------------------
    # API routes
    # ------------------------------------------------------------------

    @app.route("/api/heart-rate/<date>")
    def api_heart_rate(date):
        if not _is_today(date):
            cached = _read_cache("heart-rate", date)
            if cached is not None:
                return jsonify(cached)
        try:
            data = client.get_heart_rate(date)
            if not _is_empty(data) and not _is_today(date):
                _write_cache("heart-rate", date, data)
            return jsonify(data)
        except (ZeppAuthError, ZeppAPIError) as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/sleep/<date>")
    def api_sleep(date):
        if not _is_today(date):
            cached = _read_cache("sleep", date)
            if cached is not None:
                return jsonify(cached)
        try:
            data = client.get_sleep(date)
            if not _is_empty(data) and not _is_today(date):
                _write_cache("sleep", date, data)
            return jsonify(data)
        except (ZeppAuthError, ZeppAPIError) as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/steps/<date>")
    def api_steps(date):
        if not _is_today(date):
            cached = _read_cache("steps", date)
            if cached is not None:
                return jsonify(cached)
        try:
            data = client.get_steps(date)
            if not _is_empty(data) and not _is_today(date):
                _write_cache("steps", date, data)
            return jsonify(data)
        except (ZeppAuthError, ZeppAPIError) as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/stress/<date>")
    def api_stress(date):
        if not _is_today(date):
            cached = _read_cache("stress", date)
            if cached is not None:
                return jsonify(cached)
        try:
            data = client.get_stress(date, date)
            if not _is_empty(data) and not _is_today(date):
                _write_cache("stress", date, data)
            return jsonify(data)
        except (ZeppAuthError, ZeppAPIError) as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/training-load")
    def api_training_load():
        today = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"training-load-{today}"
        cached = _read_cache("training-load", cache_key)
        if cached is not None:
            return jsonify(cached)
        try:
            data = client.get_training_load(today, today)
            if not _is_empty(data):
                _write_cache("training-load", cache_key, data)
            return jsonify(data)
        except (ZeppAuthError, ZeppAPIError) as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/sport-load")
    @app.route("/api/sport-load/<date>")
    def api_sport_load(date=None):
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        cache_key = f"sport-load-{date}"
        if not _is_today(date):
            cached = _read_cache("sport-load", cache_key)
            if cached is not None:
                return jsonify(cached)
        try:
            data = client.get_sport_load(date, date)
            if not _is_empty(data) and not _is_today(date):
                _write_cache("sport-load", cache_key, data)
            return jsonify(data)
        except (ZeppAuthError, ZeppAPIError) as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/phn/<date>")
    def api_phn(date):
        if not _is_today(date):
            cached = _read_cache("phn", date)
            if cached is not None:
                return jsonify(cached)
        try:
            data = client.get_phn(date, date)
            if not _is_empty(data) and not _is_today(date):
                _write_cache("phn", date, data)
            return jsonify(data)
        except (ZeppAuthError, ZeppAPIError) as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/summary/<date>")
    def api_summary(date):
        """Combined summary for the dashboard -- one call, all data."""
        if not _is_today(date):
            cached = _read_cache("summary", date)
            if cached is not None:
                return jsonify(cached)
        try:
            summary = {}

            hr = client.get_heart_rate(date)
            if hr:
                bpms = [r["bpm"] for r in hr]
                summary["heart_rate"] = {
                    "readings": len(hr),
                    "avg": sum(bpms) // len(bpms),
                    "min": min(bpms),
                    "max": max(bpms),
                }
            else:
                summary["heart_rate"] = None

            sleep = client.get_sleep(date)
            summary["sleep"] = sleep if sleep else None

            steps = client.get_steps(date)
            summary["steps"] = steps if steps else None

            stress = client.get_stress(date, date)
            if stress:
                s = stress[0]
                summary["stress"] = {
                    "avg": s.get("avg_stress"),
                    "max": s.get("max_stress"),
                    "min": s.get("min_stress"),
                    "zones": s.get("zone_percentages"),
                }
            else:
                summary["stress"] = None

            if not _is_today(date):
                _write_cache("summary", date, summary)
            return jsonify(summary)
        except (ZeppAuthError, ZeppAPIError) as e:
            return jsonify({"error": str(e)}), 500

    return app
