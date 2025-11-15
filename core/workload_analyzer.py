from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict


@dataclass
class DoctorWorkload:
    doctor_id: str
    name: str
    total_hours: float
    total_shifts: int
    day_shifts: int
    night_shifts: int
    weekend_shifts: int
    burnout_index: float  # 0–100 risk score

    def to_dict(self):
        return {
            "doctor_id": self.doctor_id,
            "name": self.name,
            "total_hours": self.total_hours,
            "total_shifts": self.total_shifts,
            "day_shifts": self.day_shifts,
            "night_shifts": self.night_shifts,
            "weekend_shifts": self.weekend_shifts,
            "burnout_index": self.burnout_index,
        }


# ---------------------------------------------------------------------
# MAIN FUNCTION: compute_workload
# ---------------------------------------------------------------------
def compute_workload(doctors, shifts, assignments):
    """
    doctors: list[Doctor]
    shifts: list[Shift]
    assignments: list[Assignment]
    """

    # Make lookup tables
    doctor_lookup = {d.id: d for d in doctors}
    shift_lookup = {s.id: s for s in shifts}

    # Storage for aggregated calculations
    shift_count = defaultdict(int)
    hours_worked = defaultdict(float)
    day_count = defaultdict(int)
    night_count = defaultdict(int)
    weekend_count = defaultdict(int)

    # -------------------------------------------------------
    # PROCESS EACH ASSIGNMENT
    # -------------------------------------------------------
    for a in assignments:
        sh = shift_lookup[a.shift_id]
        doc_id = a.doctor_id

        shift_count[doc_id] += 1
        hours_worked[doc_id] += sh.duration_hours

        # Day vs Night classification
        if sh.start.hour >= 21 or sh.end.hour <= 7:
            night_count[doc_id] += 1
        else:
            day_count[doc_id] += 1

        # Weekend classification
        if sh.is_weekend:
            weekend_count[doc_id] += 1

    # -------------------------------------------------------
    # BUILD DoctorWorkload OBJECTS
    # -------------------------------------------------------
    results = []

    for d in doctors:
        total_hours = hours_worked[d.id]
        total_shifts = shift_count[d.id]

        # Simple burnout score (expand later)
        # 40 hours baseline → 0 risk
        # 160+ hours → 100 risk
        burnout = min(100, max(0, (total_hours - 40) / (160 - 40) * 100))

        results.append(
            DoctorWorkload(
                doctor_id=d.id,
                name=d.name,
                total_hours=total_hours,
                total_shifts=total_shifts,
                day_shifts=day_count[d.id],
                night_shifts=night_count[d.id],
                weekend_shifts=weekend_count[d.id],
                burnout_index=round(burnout, 1),
            )
        )

    return results

