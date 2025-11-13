# core/models.py
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

@dataclass
class Doctor:
    id: str
    name: str
    level: str              # "MO", "Reg", "Consultant", etc.
    firm: Optional[int] = None
    contract_hours_per_month: int = 175
    min_shifts_per_month: int = 16
    max_shifts_per_month: int = 18

@dataclass
class Shift:
    id: str
    name: str
    start: datetime
    end: datetime
    is_weekend: bool
    is_night: bool
    intensity: int = 3       # 1–5 for burnout weighting
    min_doctors: int = 1
    max_doctors: int = 2

    @property
    def duration_hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600.0

@dataclass
class Assignment:
    doctor_id: str
    shift_id: str

@dataclass
class Roster:
    doctors: List[Doctor]
    shifts: List[Shift]
    assignments: List[Assignment] = field(default_factory=list)

