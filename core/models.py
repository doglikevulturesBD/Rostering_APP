from dataclasses import dataclass
from datetime import datetime


# --------------------------------------------------------
# DOCTOR OBJECT
# --------------------------------------------------------
@dataclass
class Doctor:
    id: str
    name: str
    level: str
    firm: int | None
    contract_hours_per_month: int
    min_shifts_per_month: int
    max_shifts_per_month: int
    active: bool = True


# --------------------------------------------------------
# SHIFT OBJECT
# --------------------------------------------------------
@dataclass
class Shift:
    id: int
    start: datetime
    end: datetime
    duration_hours: float
    min_doctors: int
    max_doctors: int
    is_weekend: bool

    def to_dict(self):
        return {
            "id": self.id,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "duration_hours": self.duration_hours,
            "min_doctors": self.min_doctors,
            "max_doctors": self.max_doctors,
            "is_weekend": self.is_weekend,
        }


# --------------------------------------------------------
# ASSIGNMENT OBJECT (single allocation)
# --------------------------------------------------------
@dataclass
class Assignment:
    doctor_id: str
    shift_id: int
    shift_start: str
    shift_end: str


# --------------------------------------------------------
# RESULT OBJECT (collection)
# --------------------------------------------------------
@dataclass
class AssignmentResult:
    assignments: list[Assignment]

