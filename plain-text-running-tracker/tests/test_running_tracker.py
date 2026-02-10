"""Tests for running_tracker.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import running_tracker
from running_tracker import (
    format_pace,
    parse_apple_runs,
    parse_garmin_runs,
    write_markdown,
)

# --- format_pace tests ---


def test_format_pace_normal():
    assert format_pace(30.0, 5.0) == "6:00"


def test_format_pace_zero_distance():
    assert format_pace(30.0, 0) == "N/A"


def test_format_pace_negative_distance():
    assert format_pace(30.0, -1) == "N/A"


def test_format_pace_fractional():
    assert format_pace(32.5, 5.0) == "6:30"


def test_format_pace_fast():
    assert format_pace(25.0, 5.0) == "5:00"


# --- parse_garmin_runs tests ---


def test_parse_garmin_runs_returns_list(tmp_path, monkeypatch):
    # Empty directory should return empty list
    monkeypatch.setattr(running_tracker, "GARMIN_PATH", str(tmp_path))
    result = parse_garmin_runs()
    assert result == []


def test_parse_garmin_runs_valid_structure(monkeypatch):
    # Use actual garmin directory with real files
    garmin_path = Path(__file__).parent.parent / "garmin"
    if not garmin_path.exists() or not list(garmin_path.glob("*.fit")):
        return  # Skip if no garmin files available

    monkeypatch.setattr(running_tracker, "GARMIN_PATH", str(garmin_path))
    result = parse_garmin_runs()

    assert len(result) > 0
    run = result[0]
    assert "date" in run
    assert "distance" in run
    assert "duration" in run
    assert "pace" in run
    assert isinstance(run["distance"], float)
    assert isinstance(run["duration"], float)


# --- parse_apple_runs tests ---


def test_parse_apple_runs_with_minimal_xml(tmp_path, monkeypatch):
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning"
             duration="30.5"
             startDate="2025-03-15 09:00:00 +0000">
        <WorkoutStatistics type="HKQuantityTypeIdentifierDistanceWalkingRunning" sum="5.02"/>
    </Workout>
</HealthData>
"""
    xml_file = tmp_path / "export.xml"
    xml_file.write_text(xml_content)

    monkeypatch.setattr(running_tracker, "XML_PATH", str(xml_file))
    result = parse_apple_runs()

    assert len(result) == 1
    assert result[0]["date"] == "2025-03-15"
    assert result[0]["distance"] == 5.02
    assert result[0]["duration"] == 30.5


def test_parse_apple_runs_filters_non_running(tmp_path, monkeypatch):
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeCycling"
             duration="60.0"
             startDate="2025-03-15 09:00:00 +0000">
        <WorkoutStatistics type="HKQuantityTypeIdentifierDistanceWalkingRunning" sum="20.0"/>
    </Workout>
</HealthData>
"""
    xml_file = tmp_path / "export.xml"
    xml_file.write_text(xml_content)

    monkeypatch.setattr(running_tracker, "XML_PATH", str(xml_file))
    result = parse_apple_runs()

    assert result == []


def test_parse_apple_runs_filters_by_date(tmp_path, monkeypatch):
    # Date outside the START_DATE to END_DATE range
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning"
             duration="30.0"
             startDate="2024-01-01 09:00:00 +0000">
        <WorkoutStatistics type="HKQuantityTypeIdentifierDistanceWalkingRunning" sum="5.0"/>
    </Workout>
</HealthData>
"""
    xml_file = tmp_path / "export.xml"
    xml_file.write_text(xml_content)

    monkeypatch.setattr(running_tracker, "XML_PATH", str(xml_file))
    result = parse_apple_runs()

    assert result == []


# --- write_markdown tests ---


def test_write_markdown_creates_table(tmp_path, monkeypatch):
    output_file = tmp_path / "runs.md"
    monkeypatch.setattr(running_tracker, "OUTPUT_PATH", str(output_file))

    runs = [
        {"date": "2025-03-15", "distance": 5.02, "duration": 30.5, "pace": "6:04"},
        {"date": "2025-03-16", "distance": 5.0, "duration": 29.0, "pace": "5:48"},
    ]
    write_markdown(runs)

    content = output_file.read_text()
    assert "# Running Activities" in content
    assert "| Date | Distance (km) | Time (min) | Pace (min/km) |" in content
    assert "| 2025-03-15 | 5.02 | 30.5 | 6:04 |" in content
    assert "| 2025-03-16 | 5.0 | 29.0 | 5:48 |" in content
    assert "**Total runs:** 2" in content


def test_write_markdown_empty_runs(tmp_path, monkeypatch):
    output_file = tmp_path / "runs.md"
    monkeypatch.setattr(running_tracker, "OUTPUT_PATH", str(output_file))

    write_markdown([])

    content = output_file.read_text()
    assert "**Total runs:** 0" in content
