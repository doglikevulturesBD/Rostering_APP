# core/models.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


# ---------------------------------------------------------
# Doctor Model
# ---------------------------------------------------------
@dataclass
class Doctor:
    id: str
    name: str
    level: str                    # MO, Registrar, Consultant, CS
    firm: Optional[int]           # optional grouping (e.g., Firm 1/2)
    contract_hours_per_month: int
    min_shifts_per_month: int
    max_shifts_per_month: int


# ---------------------------------------------------------
# Shift Model
# ---------------------------------------------------------
@dataclass
class Shift:
    id: str                       # "S0001"
    name: str                     # "WKD_07-18_03"
    start: datetime               # timestamp
    end: datetime
    is_weekend: bool
    is_night: bool
    intensity: int                # 1–5, for burnout modelling
    min_doctors: int
    max_doctors: int

    @staticmethod
    def from_dict(row: dict) -> "Shift":
        """
        Convert a dict (e.g. from pandas DataFrame) into a Shift dataclass.
        This version is robust and accepts multiple column names.
        """

        # ---- ID ----
        sid = (
            row.get("id")
            or row.get("shift_id")
            or row.get("shiftId")
            or row.get("SID")
        )
        if sid is None:
            raise ValueError(f"Missing shift ID in row: {row}")

        # ---- Name ----
        name = (
            row.get("name")
            or row.get("shift_name")
            or row.get("shiftName")
            or f"Shift_{sid}"
        )

        # ---- Start datetime ----
        start_str = (
            row.get("start")
            or row.get("start_time")
            or row.get("Start")
            or row.get("startTime")
        )
        if start_str is None:
            raise ValueError(f"Missing 'start' field in row: {row}")

        start_dt = datetime.fromisoformat(str(start_str))

        # ---- End datetime ----
        end_str = (
            row.get("end")
            or row.get("end_time")
            or row.get("End")
            or row.get("endTime")
        )
        if end_str is None:
            raise ValueError(f"Missing 'end' field in row: {row}")

        end_dt = datetime.fromisoformat(str(end_str))

        # ---- Boolean flags ----
        is_weekend = bool(int(row.get("is_weekend", 0)))
        is_night = bool(int(row.get("is_night", 0)))

        # ---- Integers with fallback ----
        intensity = int(row.get("intensity", 3))
        min_docs = int(row.get("min_doctors", 1))
        max_docs = int(row.get("max_doctors", 1))

        return Shift(
            id=str(sid),
            name=str(name),
            start=start_dt,
            end=end_dt,
            is_weekend=is_weekend,
            is_night=is_night,
            intensity=intensity,
            min_doctors=min_docs,
            max_doctors=max_docs,
        )


# ---------------------------------------------------------
# Assignment + Roster containers
# ---------------------------------------------------------
@dataclass
class Assignment:
    doctor_id: str               # e.g., "D01"
    shift_id: str                # e.g., "S0042"


@dataclass
class Roster:
    doctors: List[Doctor]
    shifts: List[Shift]
    assignments: List[Assignment] = field(default_factory=list)
