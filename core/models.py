from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional


@dataclass
class Doctor:
    id: str
    name: str
    level: str
    firm: Optional[int]
    contract_hours_per_month: int
    min_shifts_per_month: int
    max_shifts_per_month: int


@dataclass
class Shift:
    shift_id: str
    date: datetime
    start: time
    end: time
    hours: float
    shift_type: str       # e.g. "DAY", "NIGHT", "WEEKEND"
    weekday: int
    max_doctors: int      # e.g. 1, 2, 3
    min_doctors: int      # later you will use this
    is_night: bool
    is_weekend: bool

    @staticmethod
    def from_dict(row: dict) -> "Shift":
        """Convert a CSV/dict row into a Shift dataclass."""
        # Expected keys: shift_id, date, start, end, hours, shift_type, weekday, max_doctors, min_doctors

        start = datetime.strptime(row["start"], "%H:%M").time()
        end = datetime.strptime(row["end"], "%H:%M").time()

        date = datetime.strptime(row["date"], "%Y-%m-%d")

        return Shift(
            shift_id=row["shift_id"],
            date=date,
            start=start,
            end=end,
            hours=float(row["hours"]),
            shift_type=row["shift_type"],
            weekday=int(row["weekday"]),
            max_doctors=int(row.get("max_doctors", 1)),
            min_doctors=int(row.get("min_doctors", 1)),
            is_night=row["shift_type"].upper() == "NIGHT",
            is_weekend=date.weekday() >= 5,
        )
