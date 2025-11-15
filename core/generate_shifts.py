# core/generate_shifts.py

from datetime import datetime, date, time, timedelta
from typing import List, Dict

from core.database import save_generated_shifts


def _make_datetime(d: date, h: int, m: int = 0) -> datetime:
    return datetime(d.year, d.month, d.day, h, m)


def _add_shift_row(
    rows: List[Dict],
    d: date,
    start_h: int,
    start_m: int,
    end_h: int,
    end_m: int,
    min_docs: int,
    max_docs: int,
    is_weekend: bool,
):
    """Helper to append a single shift row with proper duration + ISO strings."""
    start_dt = _make_datetime(d, start_h, start_m)
    end_dt = _make_datetime(d, end_h, end_m)

    # Handle overnight shifts (end next day)
    if end_dt <= start_dt:
        end_dt = end_dt + timedelta(days=1)

    duration_hours = (end_dt - start_dt).total_seconds() / 3600.0

    rows.append(
        {
            "date": d.isoformat(),
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "duration_hours": duration_hours,
            "min_doctors": min_docs,
            "max_doctors": max_docs,
            "is_weekend": 1 if is_weekend else 0,
        }
    )


def generate_shifts_for_month(year: int, month: int) -> None:
    """
    Generate all shifts for a given month and save them to the DB.

    Uses the following templates:

    WEEKDAYS (Mon–Fri)
    - 07:00–18:00  -> min=2, max=2
    - 09:00–20:00  -> min=1, max=1
    - 11:00–22:00  -> min=0, max=1  (preferred 1, but can be 0)
    - 14:00–01:00  -> min=3, max=4  (preferred 4, but must have 3)
    - 22:00–09:00  -> min=3, max=3

    WEEKENDS (Sat–Sun)
    - 07:00–19:00  -> min=2, max=2
    - 09:00–21:00  -> min=1, max=1
    - 11:00–23:00  -> min=1, max=1
    - 13:00–01:00  -> min=2, max=2
    - 21:00–09:00  -> min=3, max=3
    """
    rows: List[Dict] = []

    # Determine first and last day of the month
    first_day = date(year, month, 1)
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)

    d = first_day
    while d < next_month:
        weekday_index = d.weekday()  # 0=Mon, ..., 5=Sat, 6=Sun
        is_weekend = weekday_index >= 5  # Sat/Sun

        if not is_weekend:
            # -----------------------------
            # WEEKDAY SHIFTS (Mon–Fri)
            # -----------------------------

            # 07:00–18:00 (must have 2)
            _add_shift_row(
                rows,
                d,
                start_h=7,
                start_m=0,
                end_h=18,
                end_m=0,
                min_docs=2,
                max_docs=2,
                is_weekend=False,
            )

            # 09:00–20:00 (must have 1)
            _add_shift_row(
                rows,
                d,
                start_h=9,
                start_m=0,
                end_h=20,
                end_m=0,
                min_docs=1,
                max_docs=1,
                is_weekend=False,
            )

            # 11:00–22:00 (preferred 1, can be 0)
            _add_shift_row(
                rows,
                d,
                start_h=11,
                start_m=0,
                end_h=22,
                end_m=0,
                min_docs=0,
                max_docs=1,
                is_weekend=False,
            )

            # 14:00–01:00 (min 3, max 4)
            _add_shift_row(
                rows,
                d,
                start_h=14,
                start_m=0,
                end_h=1,
                end_m=0,
                min_docs=3,
                max_docs=4,
                is_weekend=False,
            )

            # 22:00–09:00 (must have 3)
            _add_shift_row(
                rows,
                d,
                start_h=22,
                start_m=0,
                end_h=9,
                end_m=0,
                min_docs=3,
                max_docs=3,
                is_weekend=False,
            )

        else:
            # -----------------------------
            # WEEKEND SHIFTS (Sat–Sun)
            # -----------------------------

            # 07:00–19:00 (must have 2)
            _add_shift_row(
                rows,
                d,
                start_h=7,
                start_m=0,
                end_h=19,
                end_m=0,
                min_docs=2,
                max_docs=2,
                is_weekend=True,
            )

            # 09:00–21:00 (must have 1)
            _add_shift_row(
                rows,
                d,
                start_h=9,
                start_m=0,
                end_h=21,
                end_m=0,
                min_docs=1,
                max_docs=1,
                is_weekend=True,
            )

            # 11:00–23:00 (must have 1)
            _add_shift_row(
                rows,
                d,
                start_h=11,
                start_m=0,
                end_h=23,
                end_m=0,
                min_docs=1,
                max_docs=1,
                is_weekend=True,
            )

            # 13:00–01:00 (must have 2)
            _add_shift_row(
                rows,
                d,
                start_h=13,
                start_m=0,
                end_h=1,
                end_m=0,
                min_docs=2,
                max_docs=2,
                is_weekend=True,
            )

            # 21:00–09:00 (must have 3)
            _add_shift_row(
                rows,
                d,
                start_h=21,
                start_m=0,
                end_h=9,
                end_m=0,
                min_docs=3,
                max_docs=3,
                is_weekend=True,
            )

        d = d + timedelta(days=1)

    # Save everything into the DB
    save_generated_shifts(rows)


