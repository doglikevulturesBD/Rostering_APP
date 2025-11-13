# core/generate_shifts.py

import pandas as pd
from datetime import datetime, timedelta
import calendar

from core.models import Shift
from core.database import save_shifts, delete_all_shifts

# Weekday patterns
WEEKDAY_PATTERNS = [
    ("WKD_07-18", "07:00", "18:00", 1, 2, False, 3),
    ("WKD_08-30-18", "08:30", "18:00", 1, 2, False, 3),
    ("WKD_09-20", "09:00", "20:00", 1, 1, False, 3),
    ("WKD_11-22", "11:00", "22:00", 1, 2, False, 3),
    ("WKD_14-01", "14:00", "01:00", 3, 4, True, 4),
    ("WKD_22-09", "22:00", "09:00", 3, 3, True, 4),
]

# Weekend patterns
WEEKEND_PATTERNS = [
    ("WKE_07-19", "07:00", "19:00", 2, 2, False, 3),
    ("WKE_09-21", "09:00", "21:00", 1, 1, False, 3),
    ("WKE_11-23", "11:00", "23:00", 1, 1, False, 3),
    ("WKE_13-01", "13:00", "01:00", 2, 2, True, 4),
    ("WKE_21-09", "21:00", "09:00", 3, 3, True, 4),
]


def generate_shifts_for_month(year: int, month: int, output_csv: str):
    num_days = calendar.monthrange(year, month)[1]
    rows = []
    sid = 1

    for day in range(1, num_days + 1):
        date_obj = datetime(year, month, day)
        is_weekend = date_obj.weekday() >= 5
        patterns = WEEKEND_PATTERNS if is_weekend else WEEKDAY_PATTERNS

        for name, start_s, end_s, min_d, max_d, is_night, intensity in patterns:

            start_dt = datetime.strptime(f"{year}-{month:02}-{day:02} {start_s}",
                                         "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(f"{year}-{month:02}-{day:02} {end_s}",
                                       "%Y-%m-%d %H:%M")
            if end_dt <= start_dt:
                end_dt += timedelta(days=1)

            rows.append(
                {
                    "id": f"S{sid:04}",
                    "name": f"{name}_{day:02}",
                    "start": start_dt.isoformat(),
                    "end": end_dt.isoformat(),
                    "is_weekend": 1 if is_weekend else 0,
                    "is_night": 1 if is_night else 0,
                    "intensity": intensity,
                    "min_doctors": min_d,
                    "max_doctors": max_d,
                }
            )
            sid += 1

    # Save CSV
    df = pd.DataFrame(rows)
    df.to_csv(output_csv, index=False)

    # Create Shift objects
    shifts = [Shift.from_dict(r) for r in rows]

    # Save to DB
    delete_all_shifts()
    save_shifts(shifts)

    print(f"Generated {len(shifts)} shifts → saved CSV + DB")

