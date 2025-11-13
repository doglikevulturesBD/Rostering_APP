from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Doctor:
    id: str
    name: str
    level: str               # "MO", "Registrar", "Consultant", "Community Service"
    firm: Optional[int]      # e.g. 1, 2, 3 (optional)
    contract_hours_per_month: int
    min_shifts_per_month: int
    max_shifts_per_month: int


@dataclass
class Shift:
    id: str                  # e.g. "S0001"
    name: str                # e.g. "WKD_07-18_01"
    start: datetime          # full datetime (date + time)
    end: datetime
    is_weekend: bool
    is_night: bool
    intensity: int           # 1–5 (used for burnout weighting later)
    min_doctors: int
    max_doctors: int

    @staticmethod
    def from_dict(row: dict) -> "Shift":
        """
        Convert a dict (e.g. from pandas DataFrame.to_dict) to a Shift instance.
        Expected keys:
        id, name, start, end, is_weekend, is_night, intensity, min_doctors, max_doctors
        """
        return Shift(
            id=str(row["id"]),
            name=str(row["name"]),
            start=datetime.fromisoformat(row["start"]),
            end=datetime.fromisoformat(row["end"]),
            is_weekend=bool(row["is_weekend"]),
            is_night=bool(row["is_night"]),
            intensity=int(row["intensity"]),
            min_doctors=int(row["min_doctors"]),
            max_doctors=int(row["max_doctors"]),
        )


@dataclass
class Assignment:
    doctor_id: str           # e.g. "D01"
    shift_id: str            # e.g. "S0001"


@dataclass
class Roster:
    doctors: List[Doctor]
    shifts: List[Shift]
    assignments: List[Assignment] = field(default_factory=list)
