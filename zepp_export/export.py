"""Export functions for zepp-export.

Handles converting health data to standard file formats:
- CSV: Simple tabular format for spreadsheets
- Apple Health XML: Compatible with Apple Health import tools
"""

import csv
from datetime import datetime, timedelta, timezone
from xml.etree.ElementTree import Element, SubElement, ElementTree
from xml.dom import minidom


# Apple Health sleep stage mapping: Zepp mode -> Apple HKCategoryValue
ZEPP_TO_APPLE_SLEEP = {
    "light": "HKCategoryValueSleepAnalysisAsleepCore",
    "deep": "HKCategoryValueSleepAnalysisAsleepDeep",
    "rem": "HKCategoryValueSleepAnalysisAsleepREM",
    "awake": "HKCategoryValueSleepAnalysisAwake",
}


def export_csv(rows: list, filepath: str):
    """Export a list of data rows to CSV.

    Each row should be a dict with consistent keys. The first row's keys
    become the CSV header.

    Args:
        rows: List of dicts, each representing one data point.
        filepath: Output file path.
    """
    if not rows:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            f.write("# No data\n")
        return

    fieldnames = list(rows[0].keys())

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _apple_date(dt: datetime) -> str:
    """Format a datetime for Apple Health XML (e.g. '2026-02-06 14:30:00 -0600')."""
    return dt.strftime("%Y-%m-%d %H:%M:%S %z")


def _minute_to_datetime(date_str: str, minute: int, tz_offset_hours: int = 0) -> datetime:
    """Convert a date string and minute-of-day to a datetime.

    Args:
        date_str: Date in YYYY-MM-DD format (the base date).
        minute: Minute-of-day offset. Values > 1440 roll into the next day.
        tz_offset_hours: Timezone offset from UTC in hours (e.g. -6 for CST).
    """
    tz = timezone(timedelta(hours=tz_offset_hours))
    base = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=tz)
    return base + timedelta(minutes=minute)


def export_apple_health(
    heart_rate_data: dict = None,
    steps_data: dict = None,
    sleep_data: dict = None,
    filepath: str = "health_export.xml",
    source_name: str = "zepp-export",
    tz_offset_hours: int = -6,
):
    """Export health data to Apple Health XML format.

    Generates XML that matches the Apple Health export schema, compatible with
    third-party import tools (Health CSV Importer, Health Auto Export, etc.).

    Apple Health does not natively import XML files -- you need a third-party
    iOS app to import this data. The format matches Apple's own export format.

    Args:
        heart_rate_data: Dict of {date_str: list of {minute, time, bpm}} from
            ZeppClient.get_heart_rate(). Pass None to skip HR export.
        steps_data: Dict of {date_str: {total_steps, ...}} from
            ZeppClient.get_steps(). Pass None to skip steps export.
        sleep_data: Dict of {date_str: {stages: [{start_minute, end_minute, stage}]}}
            from ZeppClient.get_sleep(). Pass None to skip sleep export.
        filepath: Output file path.
        source_name: Source device name in the XML.
        tz_offset_hours: Timezone offset from UTC (e.g. -6 for CST, 0 for UTC).

    Returns:
        Tuple of (hr_count, steps_count, sleep_count) records written.
    """
    tz = timezone(timedelta(hours=tz_offset_hours))

    root = Element("HealthData")
    root.set("locale", "en_US")

    export_date = SubElement(root, "ExportDate")
    export_date.set("value", _apple_date(datetime.now(tz)))

    hr_count = 0
    steps_count = 0
    sleep_count = 0

    # Heart rate records
    if heart_rate_data:
        for date_str, readings in sorted(heart_rate_data.items()):
            for r in readings:
                dt = _minute_to_datetime(date_str, r["minute"], tz_offset_hours)
                record = SubElement(root, "Record")
                record.set("type", "HKQuantityTypeIdentifierHeartRate")
                record.set("sourceName", source_name)
                record.set("unit", "count/min")
                record.set("value", str(r["bpm"]))
                record.set("startDate", _apple_date(dt))
                record.set("endDate", _apple_date(dt))
                hr_count += 1

    # Step count records (one per day)
    if steps_data:
        for date_str, steps in sorted(steps_data.items()):
            if not steps or not steps.get("total_steps"):
                continue
            day_start = _minute_to_datetime(date_str, 0, tz_offset_hours)
            day_end = _minute_to_datetime(date_str, 1439, tz_offset_hours)
            record = SubElement(root, "Record")
            record.set("type", "HKQuantityTypeIdentifierStepCount")
            record.set("sourceName", source_name)
            record.set("unit", "count")
            record.set("value", str(steps["total_steps"]))
            record.set("startDate", _apple_date(day_start))
            record.set("endDate", _apple_date(day_end))
            steps_count += 1

    # Sleep analysis records (one per stage segment)
    if sleep_data:
        for date_str, sleep in sorted(sleep_data.items()):
            if not sleep or not sleep.get("stages"):
                continue

            # The date we fetched sleep from (sleep starts on previous day)
            source_date = sleep.get("fetched_from", date_str)

            for stage in sleep["stages"]:
                apple_value = ZEPP_TO_APPLE_SLEEP.get(stage["stage"])
                if not apple_value:
                    continue

                start_dt = _minute_to_datetime(
                    source_date, stage["start_minute"], tz_offset_hours
                )
                end_dt = _minute_to_datetime(
                    source_date, stage["end_minute"], tz_offset_hours
                )

                record = SubElement(root, "Record")
                record.set("type", "HKCategoryTypeIdentifierSleepAnalysis")
                record.set("sourceName", source_name)
                record.set("value", apple_value)
                record.set("startDate", _apple_date(start_dt))
                record.set("endDate", _apple_date(end_dt))
                sleep_count += 1

            # Also add an InBed record spanning the full sleep session
            if sleep.get("start") and sleep.get("end"):
                start_dt = datetime.fromisoformat(sleep["start"]).replace(tzinfo=tz)
                end_dt = datetime.fromisoformat(sleep["end"]).replace(tzinfo=tz)
                record = SubElement(root, "Record")
                record.set("type", "HKCategoryTypeIdentifierSleepAnalysis")
                record.set("sourceName", source_name)
                record.set("value", "HKCategoryValueSleepAnalysisInBed")
                record.set("startDate", _apple_date(start_dt))
                record.set("endDate", _apple_date(end_dt))
                sleep_count += 1

    # Write with pretty formatting
    xml_str = minidom.parseString(
        b"<?xml version='1.0' encoding='UTF-8'?>" +
        _element_to_bytes(root)
    ).toprettyxml(indent="  ", encoding="UTF-8")

    with open(filepath, "wb") as f:
        f.write(xml_str)

    return hr_count, steps_count, sleep_count


def _element_to_bytes(element: Element) -> bytes:
    """Convert an ElementTree element to bytes without XML declaration."""
    import io
    buf = io.BytesIO()
    tree = ElementTree(element)
    tree.write(buf, encoding="UTF-8", xml_declaration=False)
    return buf.getvalue()
