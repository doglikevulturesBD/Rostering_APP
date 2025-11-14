# core/generate_shifts.py

from datetime import datetime, timedelta, date
import csv

from core.database import save_generated_shifts


# ----------------------------------------------------
# SHIFT TEMPLATES
# ----------------------------------------------------

WEEKDAY_TEMPLATE = [
    ("07:00", "18:00", 1, 2),
    ("08:30", "18:00", 1, 2),
    ("09:00", "20:00", 1, 1),
    ("11:00", "22:00", 1, 2),
    # UPDATED
    ("14:00", "01:00", 2, 3),   # was 3–4
    ("22:00", "09:00", 2, 2),   # was 3
]

WEEKEND_TEMPLATE = [
    ("07:00", "19:00", 2, 2),
    ("09:00", "21:00", 1, 1),
    ("11:00", "23:00", 1, 1),
    ("13:00", "01:00", 2, 2),
    ("21:00", "09:00", 2, 2),  # UPDATED: 3 → 2
]


# ----------------------------------------------------
# SHIFT BUILDER
# ----------------------------------------------------

def build_shift(start_str, end_str, min_docs, max_docs, day):
    """Return a dict representing a shift expanded for a specific date."""
    start_dt = datetime.combine(day, datetime.strptime(start_str, "%H:%M").time())
    end_dt_raw = datetime.combine(day, datetime.strptime(end_str, "%H:%M").time())

    # handle midnight crossing
    if end_dt_raw <= start_dt:
        end_dt = end_dt_raw + timedelta(days=1)
    else:
        end_dt = end_dt_raw

    duration_hours = (end_dt - start_dt).total_seconds() / 3600

    return {
        "date": day.isoformat(),
        "start_time": start_dt.isoformat(),
        "end_time": end_dt.isoformat(),
        "duration_hours": duration_hours,
        "min_doctors": min_docs,
        "max_doctors": max_docs,
        "is_weekend": 1 if day.weekday() >= 5 else 0,
    }


def generate_shifts_for_month(year: int, month: int, csv_output_path: str):
    """
    Generate all weekday/weekend shifts for the given month,
    write to CSV and DB.
    """
    # find number of days in month
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)

    num_days = (next_month - date(year, month, 1)).days

    shift_rows = []

    for day_num in range(1, num_days + 1):
        day = date(year, month, day_num)
        template = WEEKEND_TEMPLATE if day.weekday() >= 5 else WEEKDAY_TEMPLATE

        for (start, end, min_docs, max_docs) in template:
            shift = build_shift(start, end, min_docs, max_docs, day)
            shift_rows.append(shift)

    # save to DB
    save_generated_shifts(shift_rows)

    # save to CSV for preview
    fieldnames = [
        "date",
        "start_time",
        "end_time",
        "duration_hours",
        "min_doctors",
        "max_doctors",
        "is_weekend",
    ]

    with open(csv_output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(shift_rows)

    return shift_rows

