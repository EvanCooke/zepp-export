"""Decoders for Zepp/Huami API response data.

The Zepp API returns data in several non-standard formats:
- Base64-encoded JSON strings (summary fields)
- Base64-encoded binary (heart rate timelines, activity data)
- JSON strings embedded inside JSON fields (stress data)

These decoders handle all of that.
"""

import base64
import json

from .exceptions import ZeppDecodeError


def decode_summary(raw_b64: str) -> dict:
    """Decode a base64-encoded JSON summary string.

    Used for the ``summary`` field in band_data responses, which contains
    steps, sleep, and heart rate summary data.

    Args:
        raw_b64: Base64-encoded JSON string.

    Returns:
        Decoded dictionary with keys like ``stp`` (steps), ``slp`` (sleep),
        ``hr`` (heart rate summary).

    Raises:
        ZeppDecodeError: If the string can't be decoded.
    """
    try:
        decoded_bytes = base64.b64decode(raw_b64)
        return json.loads(decoded_bytes)
    except (base64.binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ZeppDecodeError(f"Failed to decode summary: {e}") from e


def decode_heart_rate(raw_b64: str) -> list:
    """Decode base64-encoded binary heart rate data to valid readings only.

    The ``data_hr`` field in band_data contains 1440 bytes -- one byte per
    minute of the day (00:00 to 23:59). Each byte is a heart rate reading
    in BPM. Values of 0 or >= 254 indicate no reading for that minute.

    Args:
        raw_b64: Base64-encoded binary heart rate data.

    Returns:
        List of dicts, each with:
        - ``minute``: minute of day (0-1439)
        - ``time``: formatted time string ``"HH:MM"``
        - ``bpm``: heart rate value

        Only includes minutes with valid readings (0 < bpm < 254).

    Raises:
        ZeppDecodeError: If the data can't be decoded.
    """
    try:
        hr_bytes = base64.b64decode(raw_b64)
    except base64.binascii.Error as e:
        raise ZeppDecodeError(f"Failed to decode heart rate data: {e}") from e

    readings = []
    for minute, bpm in enumerate(hr_bytes):
        if 0 < bpm < 254:
            readings.append({
                "minute": minute,
                "time": f"{minute // 60:02d}:{minute % 60:02d}",
                "bpm": bpm,
            })
    return readings


def decode_heart_rate_raw(raw_b64: str) -> list:
    """Decode heart rate data to a raw list of all values.

    Unlike :func:`decode_heart_rate`, this returns ALL values (typically 1440)
    including zeros and invalid readings. Useful for charting the full timeline.

    Args:
        raw_b64: Base64-encoded binary heart rate data.

    Returns:
        List of integers (one per minute). 0 or >= 254 means no reading.

    Raises:
        ZeppDecodeError: If the data can't be decoded.
    """
    try:
        hr_bytes = base64.b64decode(raw_b64)
        return list(hr_bytes)
    except base64.binascii.Error as e:
        raise ZeppDecodeError(f"Failed to decode heart rate data: {e}") from e


def decode_stress_data(data_string: str) -> list:
    """Decode stress timeline data from a JSON string.

    The stress ``data`` field is a JSON *string* (not a JSON object) containing
    an array of ``{time, value}`` pairs at 5-minute intervals.

    Args:
        data_string: JSON string like
            ``'[{"time":1770357600000,"value":47},...]'``

    Returns:
        List of dicts, each with:
        - ``time``: Unix timestamp in milliseconds
        - ``value``: Stress level (1-100)

        Stress zones: 1-25 Relaxed, 26-50 Normal, 51-75 Medium, 76-100 High.

    Raises:
        ZeppDecodeError: If the string can't be parsed.
    """
    try:
        return json.loads(data_string)
    except (json.JSONDecodeError, TypeError) as e:
        raise ZeppDecodeError(f"Failed to decode stress data: {e}") from e
