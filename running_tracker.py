#!/usr/bin/env python3
"""Parse Apple Health and Garmin FIT files to extract running activities."""

import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import fitdecode

XML_PATH = "apple/export.xml"
GARMIN_PATH = "garmin"
OUTPUT_PATH = "runs.md"

START_DATE = datetime(2025, 3, 12)
END_DATE = datetime(2025, 9, 30, 23, 59, 59)


def format_pace(duration_min: float, distance_km: float) -> str:
    """Format pace as M:SS per km."""
    if distance_km <= 0:
        return "N/A"
    pace_min_per_km = duration_min / distance_km
    minutes = int(pace_min_per_km)
    seconds = int((pace_min_per_km - minutes) * 60)
    return f"{minutes}:{seconds:02d}"


def parse_apple_runs():
    runs = []

    # Use iterparse for memory efficiency with large XML
    context = ET.iterparse(XML_PATH, events=("end",))

    for event, elem in context:
        if elem.tag == "Workout":
            activity_type = elem.get("workoutActivityType", "")

            if activity_type == "HKWorkoutActivityTypeRunning":
                start_date_str = elem.get("startDate", "")
                duration = float(elem.get("duration", 0))

                # Parse date: "2025-03-15 09:05:13 +0000"
                try:
                    start_date = datetime.strptime(
                        start_date_str[:19], "%Y-%m-%d %H:%M:%S"
                    )
                except ValueError:
                    elem.clear()
                    continue

                # Filter by date range
                if not (START_DATE <= start_date <= END_DATE):
                    elem.clear()
                    continue

                # Get distance from WorkoutStatistics
                distance_km = 0.0
                for stat in elem.findall("WorkoutStatistics"):
                    if (
                        stat.get("type")
                        == "HKQuantityTypeIdentifierDistanceWalkingRunning"
                    ):
                        distance_km = float(stat.get("sum", 0))
                        break

                if distance_km > 0:
                    runs.append(
                        {
                            "date": start_date.strftime("%Y-%m-%d"),
                            "distance": round(distance_km, 2),
                            "duration": round(duration, 1),
                            "pace": format_pace(duration, distance_km),
                        }
                    )

            # Clear element to free memory
            elem.clear()

    # Sort by date
    runs.sort(key=lambda x: x["date"])
    return runs


def parse_garmin_runs():
    runs = []
    fit_files = sorted(Path(GARMIN_PATH).glob("*.fit"))

    for fit_path in fit_files:
        with fitdecode.FitReader(str(fit_path)) as fit:
            for frame in fit:
                if isinstance(frame, fitdecode.FitDataMessage):
                    if frame.name == "session":
                        sport = frame.get_value("sport")
                        if sport != "running":
                            continue

                        start_time = frame.get_value("start_time")
                        distance_m = frame.get_value("total_distance") or 0
                        duration_s = frame.get_value("total_elapsed_time") or 0

                        distance_km = distance_m / 1000
                        duration_min = duration_s / 60

                        if distance_km > 0:
                            runs.append(
                                {
                                    "date": start_time.strftime("%Y-%m-%d"),
                                    "distance": round(distance_km, 2),
                                    "duration": round(duration_min, 1),
                                    "pace": format_pace(duration_min, distance_km),
                                }
                            )
    return runs


def write_markdown(runs):
    with open(OUTPUT_PATH, "w") as f:
        f.write("# Running Activities (March 2025 - January 2026)\n\n")
        f.write("| Date | Distance (km) | Time (min) | Pace (min/km) |\n")
        f.write("|------|---------------|------------|---------------|\n")

        for run in runs:
            f.write(
                f"| {run['date']} | {run['distance']} | {run['duration']} | {run['pace']} |\n"
            )

        f.write(f"\n**Total runs:** {len(runs)}\n")


if __name__ == "__main__":
    print("Parsing Apple Health export...")
    apple_runs = parse_apple_runs()
    print(f"Found {len(apple_runs)} Apple runs")

    print("Parsing Garmin FIT files...")
    garmin_runs = parse_garmin_runs()
    print(f"Found {len(garmin_runs)} Garmin runs")

    all_runs = apple_runs + garmin_runs
    all_runs.sort(key=lambda x: x["date"])

    write_markdown(all_runs)
    print(f"Written {len(all_runs)} total runs to {OUTPUT_PATH}")
