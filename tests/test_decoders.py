"""Tests for zepp_export.decoders.

Uses hardcoded input/output pairs from real API data to verify
that all decoders produce correct results.
"""

import base64
import json
import pytest

from zepp_export.decoders import (
    decode_summary,
    decode_heart_rate,
    decode_heart_rate_raw,
    decode_stress_data,
)
from zepp_export.exceptions import ZeppDecodeError


# -----------------------------------------------------------------------
# decode_summary
# -----------------------------------------------------------------------

class TestDecodeSummary:
    """Test base64-encoded JSON summary decoding."""

    def test_basic_summary(self):
        """Decode a minimal summary with steps and sleep data."""
        original = {
            "goal": 8000,
            "stp": {"ttl": 6548, "dis": 4644, "cal": 1247},
            "slp": {"rhr": 57, "ss": 77, "dp": 127, "lt": 385},
            "tz": "-21600",
        }
        encoded = base64.b64encode(json.dumps(original).encode()).decode()

        result = decode_summary(encoded)

        assert result["goal"] == 8000
        assert result["stp"]["ttl"] == 6548
        assert result["slp"]["rhr"] == 57
        assert result["slp"]["ss"] == 77

    def test_summary_with_sleep_stages(self):
        """Decode summary containing sleep stage data."""
        original = {
            "slp": {
                "stage": [
                    {"start": 1471, "stop": 1478, "mode": 4},
                    {"start": 1479, "stop": 1508, "mode": 5},
                    {"start": 1509, "stop": 1523, "mode": 4},
                    {"start": 1524, "stop": 1540, "mode": 8},
                ],
                "rhr": 55,
                "ss": 80,
            }
        }
        encoded = base64.b64encode(json.dumps(original).encode()).decode()

        result = decode_summary(encoded)

        stages = result["slp"]["stage"]
        assert len(stages) == 4
        assert stages[0]["mode"] == 4  # light
        assert stages[1]["mode"] == 5  # deep
        assert stages[3]["mode"] == 8  # REM

    def test_invalid_base64_raises(self):
        """Invalid base64 input should raise ZeppDecodeError."""
        with pytest.raises(ZeppDecodeError, match="Failed to decode summary"):
            decode_summary("not-valid-base64!!!")

    def test_valid_base64_invalid_json_raises(self):
        """Valid base64 that doesn't contain JSON should raise ZeppDecodeError."""
        encoded = base64.b64encode(b"this is not json").decode()
        with pytest.raises(ZeppDecodeError, match="Failed to decode summary"):
            decode_summary(encoded)


# -----------------------------------------------------------------------
# decode_heart_rate
# -----------------------------------------------------------------------

class TestDecodeHeartRate:
    """Test base64-encoded binary heart rate decoding."""

    def test_basic_hr_decoding(self):
        """Decode a small HR byte array with known values."""
        # 10 bytes: minutes 0-9, with HR at specific minutes
        raw = bytes([0, 0, 0, 72, 75, 0, 0, 80, 0, 65])
        encoded = base64.b64encode(raw).decode()

        readings = decode_heart_rate(encoded)

        assert len(readings) == 4
        assert readings[0] == {"minute": 3, "time": "00:03", "bpm": 72}
        assert readings[1] == {"minute": 4, "time": "00:04", "bpm": 75}
        assert readings[2] == {"minute": 7, "time": "00:07", "bpm": 80}
        assert readings[3] == {"minute": 9, "time": "00:09", "bpm": 65}

    def test_hr_time_formatting(self):
        """Verify time strings are correctly formatted for later hours."""
        # Put a reading at minute 754 (12:34)
        raw = bytes([0] * 754 + [88] + [0] * 10)
        encoded = base64.b64encode(raw).decode()

        readings = decode_heart_rate(encoded)

        assert len(readings) == 1
        assert readings[0]["time"] == "12:34"
        assert readings[0]["bpm"] == 88

    def test_hr_filters_invalid_values(self):
        """Values of 0, 254, and 255 should be excluded."""
        raw = bytes([0, 70, 253, 254, 255, 90])
        encoded = base64.b64encode(raw).decode()

        readings = decode_heart_rate(encoded)

        assert len(readings) == 3
        bpms = [r["bpm"] for r in readings]
        assert bpms == [70, 253, 90]

    def test_empty_hr_data(self):
        """All-zero HR data should return empty list."""
        raw = bytes([0] * 100)
        encoded = base64.b64encode(raw).decode()

        readings = decode_heart_rate(encoded)

        assert readings == []

    def test_invalid_base64_raises(self):
        """Invalid base64 should raise ZeppDecodeError."""
        with pytest.raises(ZeppDecodeError, match="Failed to decode heart rate"):
            decode_heart_rate("!!!invalid!!!")


# -----------------------------------------------------------------------
# decode_heart_rate_raw
# -----------------------------------------------------------------------

class TestDecodeHeartRateRaw:
    """Test raw heart rate decoding (all values, including zeros)."""

    def test_raw_returns_all_values(self):
        """Raw decoder should return every byte, including zeros."""
        raw = bytes([0, 72, 0, 254, 80])
        encoded = base64.b64encode(raw).decode()

        result = decode_heart_rate_raw(encoded)

        assert result == [0, 72, 0, 254, 80]
        assert len(result) == 5

    def test_full_day_length(self):
        """A full day of data should return exactly 1440 values."""
        raw = bytes([65] * 1440)
        encoded = base64.b64encode(raw).decode()

        result = decode_heart_rate_raw(encoded)

        assert len(result) == 1440
        assert all(v == 65 for v in result)


# -----------------------------------------------------------------------
# decode_stress_data
# -----------------------------------------------------------------------

class TestDecodeStressData:
    """Test JSON-string-inside-JSON stress data decoding."""

    def test_basic_stress_decoding(self):
        """Decode a typical stress data JSON string."""
        readings = [
            {"time": 1770357600000, "value": 47},
            {"time": 1770357900000, "value": 57},
            {"time": 1770358200000, "value": 33},
        ]
        data_string = json.dumps(readings)

        result = decode_stress_data(data_string)

        assert len(result) == 3
        assert result[0]["time"] == 1770357600000
        assert result[0]["value"] == 47
        assert result[2]["value"] == 33

    def test_stress_five_minute_intervals(self):
        """Verify readings are 5 minutes (300000 ms) apart."""
        readings = [
            {"time": 1770357600000, "value": 40},
            {"time": 1770357900000, "value": 45},
            {"time": 1770358200000, "value": 50},
        ]
        data_string = json.dumps(readings)

        result = decode_stress_data(data_string)

        assert result[1]["time"] - result[0]["time"] == 300000
        assert result[2]["time"] - result[1]["time"] == 300000

    def test_empty_stress_array(self):
        """Empty array string should return empty list."""
        result = decode_stress_data("[]")
        assert result == []

    def test_invalid_json_raises(self):
        """Non-JSON string should raise ZeppDecodeError."""
        with pytest.raises(ZeppDecodeError, match="Failed to decode stress"):
            decode_stress_data("not json at all")

    def test_none_input_raises(self):
        """None input should raise ZeppDecodeError."""
        with pytest.raises(ZeppDecodeError, match="Failed to decode stress"):
            decode_stress_data(None)
