# core/models.py

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List


@dataclass
class Doctor:
    id: str
    name: str
    level: str
    firm: Optional[int]
    contract_hours_per_month: int
    min_shifts_per_month: int
    max_shifts_per_month: int
    active: bool = True


@dataclass
class Shift:
    id: int
    start: datetime
    end: datetime
    duration_hours: float
    min_doctors: int
    max_doctors: int
    is_weekend: bool


@dataclass
class Assignment:
    doctor_id: str
    shift_id: int


@dataclass
class Roster:
    doctors: List[Doctor]
    shifts: List[Shift]
    assignments: List[Assignment]


@dataclass
class DoctorWorkload:
    doctor_id: str
    total_shifts: int = 0
    total_hours: float = 0.0
    night_shifts: int = 0
    weekend_shifts: int = 0
    consecutive_days: int = 0
    consecutive_nights: int = 0
    rest_violations: int = 0
    burnout_score: float = 0.0
