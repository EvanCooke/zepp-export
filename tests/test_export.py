"""Tests for zepp_export.export."""

import os
import tempfile
from xml.etree.ElementTree import parse as xml_parse

from zepp_export.export import export_csv, export_apple_health


class TestExportCSV:
    """Test CSV export."""

    def test_basic_csv(self):
        rows = [
            {"date": "2026-02-06", "type": "heart_rate", "value": 72},
            {"date": "2026-02-06", "type": "heart_rate", "value": 80},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            path = f.name
        try:
            export_csv(rows, path)
            with open(path) as f:
                content = f.read()
            assert "date,type,value" in content
            assert "2026-02-06,heart_rate,72" in content
        finally:
            os.unlink(path)

    def test_empty_csv(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            path = f.name
        try:
            export_csv([], path)
            with open(path) as f:
                content = f.read()
            assert "No data" in content
        finally:
            os.unlink(path)


class TestExportAppleHealth:
    """Test Apple Health XML export."""

    def test_heart_rate_export(self):
        """HR readings become HKQuantityTypeIdentifierHeartRate records."""
        hr_data = {
            "2026-02-06": [
                {"minute": 360, "time": "06:00", "bpm": 72},
                {"minute": 361, "time": "06:01", "bpm": 75},
            ]
        }

        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
            path = f.name
        try:
            hr_count, steps_count, sleep_count = export_apple_health(
                heart_rate_data=hr_data,
                filepath=path,
                tz_offset_hours=-6,
            )

            assert hr_count == 2
            assert steps_count == 0
            assert sleep_count == 0

            tree = xml_parse(path)
            root = tree.getroot()
            records = root.findall("Record")
            assert len(records) == 2

            r = records[0]
            assert r.get("type") == "HKQuantityTypeIdentifierHeartRate"
            assert r.get("unit") == "count/min"
            assert r.get("value") == "72"
            assert "2026-02-06" in r.get("startDate")
            assert "06:00" in r.get("startDate")
        finally:
            os.unlink(path)

    def test_steps_export(self):
        """Step data becomes HKQuantityTypeIdentifierStepCount records."""
        steps_data = {
            "2026-02-06": {"total_steps": 6548, "distance_meters": 4644},
        }

        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
            path = f.name
        try:
            hr_count, steps_count, sleep_count = export_apple_health(
                steps_data=steps_data,
                filepath=path,
            )

            assert steps_count == 1

            tree = xml_parse(path)
            records = tree.findall("Record")
            assert len(records) == 1

            r = records[0]
            assert r.get("type") == "HKQuantityTypeIdentifierStepCount"
            assert r.get("value") == "6548"
            assert r.get("unit") == "count"
        finally:
            os.unlink(path)

    def test_sleep_stage_mapping(self):
        """Zepp sleep stages map to correct Apple HKCategoryValues."""
        sleep_data = {
            "2026-02-06": {
                "fetched_from": "2026-02-05",
                "start": "2026-02-05T23:30:00",
                "end": "2026-02-06T07:15:00",
                "stages": [
                    {"start_minute": 1410, "end_minute": 1440, "duration_minutes": 30, "stage": "light"},
                    {"start_minute": 1440, "end_minute": 1470, "duration_minutes": 30, "stage": "deep"},
                    {"start_minute": 1470, "end_minute": 1490, "duration_minutes": 20, "stage": "rem"},
                    {"start_minute": 1490, "end_minute": 1500, "duration_minutes": 10, "stage": "awake"},
                ],
                "nap_stages": [],
            }
        }

        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
            path = f.name
        try:
            hr_count, steps_count, sleep_count = export_apple_health(
                sleep_data=sleep_data,
                filepath=path,
                tz_offset_hours=-6,
            )

            # 4 stage records + 1 InBed record = 5
            assert sleep_count == 5

            tree = xml_parse(path)
            records = tree.findall("Record")
            sleep_records = [
                r for r in records
                if r.get("type") == "HKCategoryTypeIdentifierSleepAnalysis"
            ]
            assert len(sleep_records) == 5

            values = [r.get("value") for r in sleep_records]
            assert "HKCategoryValueSleepAnalysisAsleepCore" in values
            assert "HKCategoryValueSleepAnalysisAsleepDeep" in values
            assert "HKCategoryValueSleepAnalysisAsleepREM" in values
            assert "HKCategoryValueSleepAnalysisAwake" in values
            assert "HKCategoryValueSleepAnalysisInBed" in values
        finally:
            os.unlink(path)

    def test_combined_export(self):
        """All data types in a single export."""
        hr_data = {"2026-02-06": [{"minute": 400, "time": "06:40", "bpm": 68}]}
        steps_data = {"2026-02-06": {"total_steps": 5000}}
        sleep_data = {
            "2026-02-06": {
                "fetched_from": "2026-02-05",
                "start": "2026-02-05T23:00:00",
                "end": "2026-02-06T07:00:00",
                "stages": [
                    {"start_minute": 1380, "end_minute": 1440, "duration_minutes": 60, "stage": "light"},
                ],
                "nap_stages": [],
            }
        }

        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
            path = f.name
        try:
            hr_count, steps_count, sleep_count = export_apple_health(
                heart_rate_data=hr_data,
                steps_data=steps_data,
                sleep_data=sleep_data,
                filepath=path,
            )

            assert hr_count == 1
            assert steps_count == 1
            assert sleep_count == 2  # 1 stage + 1 InBed

            tree = xml_parse(path)
            records = tree.findall("Record")
            types = set(r.get("type") for r in records)
            assert "HKQuantityTypeIdentifierHeartRate" in types
            assert "HKQuantityTypeIdentifierStepCount" in types
            assert "HKCategoryTypeIdentifierSleepAnalysis" in types
        finally:
            os.unlink(path)

    def test_empty_export(self):
        """Export with no data produces valid XML."""
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
            path = f.name
        try:
            hr_count, steps_count, sleep_count = export_apple_health(filepath=path)
            assert hr_count == 0
            assert steps_count == 0
            assert sleep_count == 0

            tree = xml_parse(path)
            root = tree.getroot()
            assert root.tag == "HealthData"
        finally:
            os.unlink(path)
