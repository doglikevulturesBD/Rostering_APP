# core/models.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


# ---------------------------------------------------------
# Doctor Model
# ---------------------------------------------------------
@dataclass
class Doctor:
    id: str                                # e.g. "D01"
    name: str                              # Doctor name
    level: str                             # MO, Registrar, Consultant, Community Service
    firm: Optional[int]                    # ED Firm/team (optional)
    contract_hours_per_month: int          # e.g. 175
    min_shifts_per_month: int              # e.g. 16
    max_shifts_per_month: int              # e.g. 18


# ---------------------------------------------------------
# Shift Model
# ---------------------------------------------------------
@dataclass
class Shift:
    id: str                                # "S0001"
    name: str                              # "WKD_07-18_01"
    start: datetime                        # Full datetime
    end: datetime
    is_weekend: bool                       # weekend flag
    is_night: bool                         # night shift flag
    intensity: int                         # 1–5 (used later for burnout models)
    min_doctors: int                       # required minimum coverage
    max_doctors: int                       # allowed maximum coverage

    @staticmethod
    def from_dict(row: dict) -> "Shift":
        """
        Converts a CSV row or DB row into a Shift dataclass.
        This is robust and allows multiple naming conventions.
        Expected keys may include:
        - id or shift_id
        - name or shift_name
        - start or start_time
        - end or end_time
        - is_weekend
        - is_night
        - intensity
        - min_doctors / max_doctors
        """
        # ---- Shift ID ----
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
        start_raw = (
            row.get("start")
            or row.get("start_time")
            or row.get("Start")
            or row.get("startTime")
        )
        if start_raw is None:
            raise ValueError(f"Missing 'start' field in row: {row}")

        start_dt = datetime.fromisoformat(str(start_raw))

        # ---- End datetime ----
        end_raw = (
            row.get("end")
            or row.get("end_time")
            or row.get("End")
            or row.get("endTime")
        )
        if end_raw is None:
            raise ValueError(f"Missing 'end' field in row: {row}")

        end_dt = datetime.fromisoformat(str(end_raw))

        # ---- Boolean flags ----
        is_weekend = bool(int(row.get("is_weekend", 0)))
        is_night = bool(int(row.get("is_night", 0)))

        # ---- Integer values ----
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
# Assignment + Roster Models
# ---------------------------------------------------------
@dataclass
class Assignment:
    doctor_id: str                         # e.g. "D03"
    shift_id: str                          # e.g. "S0041"


@dataclass
class Roster:
    doctors: List[Doctor]
    shifts: List[Shift]
    assignments: List[Assignment] = field(default_factory=list)
