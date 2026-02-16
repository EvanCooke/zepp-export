"""Zepp/Huami Cloud API client.

Provides programmatic access to health data from Amazfit/Zepp wearable devices.
Wraps the unofficial Huami Cloud API with built-in decoding for all data formats.

Example::

    from zepp_export import ZeppClient

    client = ZeppClient(token="your_token", user_id="your_id")
    hr = client.get_heart_rate("2026-02-06")
    print(f"Got {len(hr)} heart rate readings")
"""

import base64

import requests
from datetime import datetime, timedelta

from .decoders import decode_summary, decode_heart_rate, decode_heart_rate_raw, decode_stress_data
from .exceptions import ZeppAuthError, ZeppAPIError, ZeppDecodeError

SLEEP_STAGES = {4: "light", 5: "deep", 7: "awake", 8: "rem"}
ACTIVITY_MODES = {1: "slow_walking", 3: "fast_walking", 7: "running", 76: "light_activity"}


class ZeppClient:
    """Client for the Zepp/Huami Cloud API.

    Args:
        token: Authentication token (``apptoken``). Get one from
            https://user.huami.com/privacy/index.html browser cookies.
        user_id: Your numeric Zepp user ID.
        base_url: API base URL. Defaults to the US region.
    """

    REGIONS = {
        "us": "https://api-mifit-us2.zepp.com",
        "global": "https://api-mifit.huami.com",
        "eu": "https://api-mifit-de2.zepp.com",
    }

    def __init__(self, token: str, user_id: str, base_url: str = None):
        if not token:
            raise ZeppAuthError(
                "No token provided. Get one from "
                "https://user.huami.com/privacy/index.html "
                "or run: python -m zepp_export login"
            )
        if not user_id:
            raise ValueError("user_id is required")

        self.token = token
        self.user_id = user_id
        self.base_url = (base_url or self.REGIONS["us"]).rstrip("/")

        self._web_headers = {
            "apptoken": self.token,
            "appPlatform": "web",
            "appname": "com.xiaomi.hm.health",
        }

        self._ios_headers = {
            "apptoken": self.token,
            "appplatform": "ios_phone",
            "appname": "com.huami.midong",
            "v": "2.0",
            "timezone": "America/Chicago",
            "accept": "*/*",
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _request(self, method: str, path: str, headers: dict = None, **kwargs) -> dict:
        """Make an authenticated API request with error handling.

        Raises:
            ZeppAuthError: On 401 (token expired).
            ZeppAPIError: On other HTTP errors or API error codes.
        """
        url = f"{self.base_url}{path}"
        hdrs = headers or self._web_headers

        try:
            resp = requests.request(method, url, headers=hdrs, **kwargs)
        except requests.exceptions.RequestException as e:
            raise ZeppAPIError(f"Request failed: {e}") from e

        if resp.status_code == 401:
            raise ZeppAuthError(
                "Token expired. Get a fresh token from "
                "https://user.huami.com/privacy/index.html "
                "or run: python -m zepp_export login"
            )

        if resp.status_code != 200:
            raise ZeppAPIError(
                f"HTTP {resp.status_code}: {resp.text[:500]}",
                status_code=resp.status_code,
            )

        try:
            data = resp.json()
        except ValueError as e:
            raise ZeppAPIError(f"Invalid JSON response: {e}") from e

        return data

    @staticmethod
    def _date_to_ms(date_str: str) -> int:
        """Convert YYYY-MM-DD to unix milliseconds (start of day)."""
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return int(dt.timestamp() * 1000)

    @staticmethod
    def _end_of_day_ms(date_str: str) -> int:
        """Convert YYYY-MM-DD to unix milliseconds (end of day)."""
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return int(dt.timestamp() * 1000) + 86400000 - 1

    # ------------------------------------------------------------------
    # Band Data (HR, Sleep, Steps) -- the primary health endpoint
    # ------------------------------------------------------------------

    def _fetch_band_data(self, from_date: str, to_date: str) -> list:
        """Fetch and decode band data for a date range. Internal method."""
        data = self._request("GET", "/v1/data/band_data.json", params={
            "query_type": "detail",
            "device_type": "android_phone",
            "userid": self.user_id,
            "from_date": from_date,
            "to_date": to_date,
        })

        if data.get("code") != 1:
            raise ZeppAPIError(
                f"API error: {data.get('message', 'unknown')}",
                status_code=200,
            )

        days = []
        for day in data.get("data", []):
            result = {"date": day.get("date_time")}

            if "summary" in day and isinstance(day["summary"], str):
                try:
                    result["summary"] = decode_summary(day["summary"])
                except ZeppDecodeError:
                    result["summary"] = None

            if "data_hr" in day and isinstance(day["data_hr"], str):
                try:
                    result["heart_rate"] = decode_heart_rate(day["data_hr"])
                    result["heart_rate_raw"] = decode_heart_rate_raw(day["data_hr"])
                except ZeppDecodeError:
                    result["heart_rate"] = []
                    result["heart_rate_raw"] = []

            if "data" in day and isinstance(day["data"], str):
                try:
                    activity_bytes = base64.b64decode(day["data"])
                    result["activity_bytes_length"] = len(activity_bytes)
                except Exception:
                    pass

            days.append(result)

        return days

    def get_band_data(self, date: str) -> dict:
        """Get all band data for a single date.

        Returns the full decoded data including heart rate timeline, sleep,
        step counts, and activity information.

        Args:
            date: Date string in ``YYYY-MM-DD`` format.

        Returns:
            Dict with keys ``date``, ``summary``, ``heart_rate``,
            ``heart_rate_raw``.
        """
        days = self._fetch_band_data(date, date)
        if not days:
            return {"date": date, "summary": None, "heart_rate": [], "heart_rate_raw": []}
        return days[0]

    def get_heart_rate(self, date: str) -> list:
        """Get minute-by-minute heart rate readings for a date.

        Args:
            date: Date string in ``YYYY-MM-DD`` format.

        Returns:
            List of dicts, each with ``minute`` (0-1439), ``time`` (``"HH:MM"``),
            and ``bpm``. Only includes minutes with valid readings.

        Example::

            >>> readings = client.get_heart_rate("2026-02-06")
            >>> print(f"{readings[0]['time']}: {readings[0]['bpm']} bpm")
            06:23: 72 bpm
        """
        day = self.get_band_data(date)
        return day.get("heart_rate", [])

    def get_sleep(self, date: str) -> dict:
        """Get sleep data for a given date.

        **Sleep crosses midnight**: sleep sessions that start before midnight are
        stored on the previous day's record. This method automatically fetches
        both day N-1 and day N to find the correct session. This means **2x the
        API calls** compared to other single-day methods. When pulling 90+ days
        of sleep data, consider using :meth:`get_band_data` directly.

        Args:
            date: Date string in ``YYYY-MM-DD`` format -- the date you **woke up**.

        Returns:
            Dict with ``resting_hr``, ``sleep_score``, ``deep_minutes``,
            ``light_minutes``, ``start``, ``end``, ``duration_minutes``,
            ``stages``, ``nap_stages``, ``fetched_from``.
            Empty dict if no sleep data found.
        """
        dt = datetime.strptime(date, "%Y-%m-%d")
        prev_date = (dt - timedelta(days=1)).strftime("%Y-%m-%d")

        days = self._fetch_band_data(prev_date, date)

        best_sleep = None
        best_source_date = None

        for day in days:
            summary = day.get("summary")
            if not summary or "slp" not in summary:
                continue

            slp = summary["slp"]
            if not slp.get("ed") or not slp.get("st"):
                continue

            end_dt = datetime.fromtimestamp(slp["ed"])
            end_date_str = end_dt.strftime("%Y-%m-%d")

            if end_date_str == date:
                best_sleep = slp
                best_source_date = day["date"]
                break

            if day["date"] == date and best_sleep is None:
                best_sleep = slp
                best_source_date = day["date"]

        if not best_sleep:
            return {}

        stages = []
        for s in best_sleep.get("stage", []):
            stages.append({
                "start_minute": s["start"],
                "end_minute": s["stop"],
                "duration_minutes": s["stop"] - s["start"],
                "stage": SLEEP_STAGES.get(s["mode"], f"unknown_{s['mode']}"),
            })

        nap_stages = []
        for s in best_sleep.get("odd_stage", []):
            nap_stages.append({
                "start_minute": s["start"],
                "end_minute": s["stop"],
                "duration_minutes": s["stop"] - s["start"],
                "stage": SLEEP_STAGES.get(s["mode"], f"unknown_{s['mode']}"),
            })

        result = {
            "date": date,
            "fetched_from": best_source_date,
            "resting_hr": best_sleep.get("rhr"),
            "sleep_score": best_sleep.get("ss"),
            "deep_minutes": best_sleep.get("dp"),
            "light_minutes": best_sleep.get("lt"),
            "stages": stages,
            "nap_stages": nap_stages,
        }

        if best_sleep.get("st") and best_sleep.get("ed"):
            start = datetime.fromtimestamp(best_sleep["st"])
            end = datetime.fromtimestamp(best_sleep["ed"])
            result["start"] = start.isoformat()
            result["end"] = end.isoformat()
            result["duration_minutes"] = int((end - start).total_seconds() / 60)

        return result

    def get_steps(self, date: str) -> dict:
        """Get step and activity data for a date.

        Args:
            date: Date string in ``YYYY-MM-DD`` format.

        Returns:
            Dict with ``total_steps``, ``distance_meters``, ``calories``,
            ``run_distance_meters``, ``goal``, ``stages``.
            Empty dict if no data found.
        """
        day = self.get_band_data(date)
        summary = day.get("summary")
        if not summary or "stp" not in summary:
            return {}

        stp = summary["stp"]
        stages = []
        for s in stp.get("stage", []):
            stages.append({
                "start_minute": s["start"],
                "end_minute": s["stop"],
                "mode": ACTIVITY_MODES.get(s["mode"], f"unknown_{s['mode']}"),
                "steps": s.get("step", 0),
                "distance_meters": s.get("dis", 0),
                "calories": s.get("cal", 0),
            })

        return {
            "date": date,
            "total_steps": stp.get("ttl"),
            "distance_meters": stp.get("dis"),
            "calories": stp.get("cal"),
            "run_distance_meters": stp.get("runDist"),
            "run_calories": stp.get("runCal"),
            "goal": summary.get("goal"),
            "stages": stages,
        }

    # ------------------------------------------------------------------
    # Events API v2
    # ------------------------------------------------------------------

    def _fetch_events_v2(self, event_type: str, sub_type: str,
                         from_ms: int, to_ms: int, limit: int = 200) -> list:
        """Fetch events from /v2/users/me/events."""
        data = self._request("GET", "/v2/users/me/events",
            headers=self._ios_headers,
            params={
                "eventType": event_type,
                "subType": sub_type,
                "from": from_ms,
                "to": to_ms,
                "limit": limit,
            },
        )
        return data.get("items", [])

    def _fetch_events_v1(self, event_type: str, from_ms: int, to_ms: int,
                         sub_type: str = None, limit: int = 200) -> list:
        """Fetch events from /users/{userId}/events."""
        params = {
            "eventType": event_type,
            "from": from_ms,
            "to": to_ms,
            "limit": limit,
        }
        if sub_type:
            params["subType"] = sub_type

        data = self._request("GET", f"/users/{self.user_id}/events",
            headers=self._ios_headers,
            params=params,
        )
        return data.get("items", [])

    # ------------------------------------------------------------------
    # Stress
    # ------------------------------------------------------------------

    def get_stress(self, from_date: str, to_date: str) -> list:
        """Get stress data for a date range.

        Returns 5-minute interval stress readings derived from HRV.
        Lower stress = higher HRV.

        Args:
            from_date: Start date ``YYYY-MM-DD``.
            to_date: End date ``YYYY-MM-DD``.

        Returns:
            List of daily records, each with ``timestamp``, ``avg_stress``,
            ``max_stress``, ``min_stress``, ``zone_percentages``
            (relaxed/normal/medium/high), and ``readings`` (5-min intervals).

            Stress zones: 1-25 Relaxed, 26-50 Normal, 51-75 Medium, 76-100 High.
        """
        from_ms = self._date_to_ms(from_date)
        to_ms = self._end_of_day_ms(to_date)

        items = self._fetch_events_v1("all_day_stress", from_ms, to_ms)

        results = []
        for item in items:
            record = {
                "timestamp": item.get("timestamp"),
                "avg_stress": int(item["avgStress"]) if "avgStress" in item else None,
                "max_stress": int(item["maxStress"]) if "maxStress" in item else None,
                "min_stress": int(item["minStress"]) if "minStress" in item else None,
                "zone_percentages": {
                    "relaxed": int(item.get("relaxProportion", 0)),
                    "normal": int(item.get("normalProportion", 0)),
                    "medium": int(item.get("mediumProportion", 0)),
                    "high": int(item.get("highProportion", 0)),
                },
            }

            data_str = item.get("data", "")
            if isinstance(data_str, str) and data_str.startswith("["):
                try:
                    record["readings"] = decode_stress_data(data_str)
                except ZeppDecodeError:
                    record["readings"] = []
            else:
                record["readings"] = []

            results.append(record)

        return results

    # ------------------------------------------------------------------
    # Training Load / Exertion
    # ------------------------------------------------------------------

    def get_training_load(self, from_date: str, to_date: str) -> list:
        """Get training load (exertion) data for a date range.

        Returns Acute Training Load (ATL), Chronic Training Load (CTL), and
        Training Stress Balance (TSB). Uses ``from=0`` internally to get full
        history, since these are rolling metrics.

        Args:
            from_date: Start date ``YYYY-MM-DD``.
            to_date: End date ``YYYY-MM-DD``.

        Returns:
            List of dicts with ``timestamp``, ``exercise_score``, ``total_score``,
            ``target_score``, ``completion_percent``, ``recovery_factor``,
            ``atl``, ``ctl``, ``tsb``, ``exercise_plan``, ``activities``.
        """
        to_ms = self._end_of_day_ms(to_date)

        items = self._fetch_events_v2("exertion", "algo_result", 0, to_ms)

        results = []
        for item in items:
            val = item.get("value", {})
            plan = val.get("exercisePlan", {})
            activities = val.get("activities", [])

            results.append({
                "timestamp": item.get("timestamp"),
                "exercise_score": val.get("exerciseScore"),
                "total_score": val.get("totalScore"),
                "target_score": val.get("targetScore"),
                "completion_percent": val.get("completionPercent"),
                "recovery_factor": val.get("recoveryFactor"),
                "atl": val.get("atl"),
                "ctl": val.get("ctl"),
                "tsb": val.get("tsb"),
                "exercise_plan": {
                    "hr_lower": plan.get("heartRateLower"),
                    "hr_upper": plan.get("heartRateUpper"),
                    "duration_minutes": plan.get("duration"),
                    "intensity": plan.get("intensity"),
                } if plan else None,
                "activities": [
                    {
                        "start_minute": a.get("startTime"),
                        "end_minute": a.get("endTime"),
                        "score": a.get("currentScore"),
                    }
                    for a in activities
                ],
            })

        return results

    # ------------------------------------------------------------------
    # PHN / TRIMP
    # ------------------------------------------------------------------

    def get_phn(self, from_date: str, to_date: str) -> list:
        """Get PHN (Personal Health Number) / TRIMP data.

        TRIMP (Training Impulse) measures total training stress per day.

        Args:
            from_date: Start date ``YYYY-MM-DD``.
            to_date: End date ``YYYY-MM-DD``.

        Returns:
            List of dicts with ``timestamp``, ``trimp``, ``atl``, ``ctl``, ``tsb``.
        """
        to_ms = self._end_of_day_ms(to_date)
        items = self._fetch_events_v2("phn", "daily_analysis", 0, to_ms)

        results = []
        for item in items:
            val = item.get("value", {})
            result = val.get("result", {})
            results.append({
                "timestamp": item.get("timestamp"),
                "trimp": result.get("trimp"),
                "atl": result.get("atl"),
                "ctl": result.get("ctl"),
                "tsb": result.get("tsb"),
            })

        return results

    # ------------------------------------------------------------------
    # Sport Load / VO2 Max
    # ------------------------------------------------------------------

    def get_sport_load(self, from_date: str, to_date: str) -> list:
        """Get daily sport load and weekly training load data.

        Args:
            from_date: Start date ``YYYY-MM-DD``.
            to_date: End date ``YYYY-MM-DD``.

        Returns:
            List of dicts with ``date``, ``daily_load``, ``weekly_load``,
            ``optimal_min``, ``optimal_max``, ``overreaching``.
        """
        data = self._request("GET",
            f"/v2/watch/users/{self.user_id}/WatchSportStatistics/SPORT_LOAD",
            headers=self._ios_headers,
            params={
                "startDay": from_date,
                "endDay": to_date,
                "limit": 900,
                "isReverse": "true",
            },
        )

        results = []
        for item in data.get("items", []):
            results.append({
                "date": item.get("dayId"),
                "daily_load": item.get("currnetDayTrainLoad"),
                "weekly_load": item.get("wtlSum"),
                "optimal_min": item.get("wtlSumOptimalMin"),
                "optimal_max": item.get("wtlSumOptimalMax"),
                "overreaching": item.get("wtlSumOverreaching"),
            })

        return results

    def get_vo2_max(self, from_date: str, to_date: str) -> list:
        """Get VO2 Max estimates.

        Note: May require specific outdoor GPS workouts to generate data.
        Can return empty if no qualifying workouts exist.

        Args:
            from_date: Start date ``YYYY-MM-DD``.
            to_date: End date ``YYYY-MM-DD``.

        Returns:
            List of VO2 Max records (format varies by device).
        """
        data = self._request("GET",
            f"/v2/watch/users/{self.user_id}/WatchSportStatistics/VO2_MAX",
            headers=self._ios_headers,
            params={
                "startDay": from_date,
                "endDay": to_date,
                "limit": 900,
                "isReverse": "true",
            },
        )
        return data.get("items", [])
