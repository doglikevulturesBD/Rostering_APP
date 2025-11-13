# core/workload_analyzer.py

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List

from core.models import Doctor, Shift, Assignment


# ==========================================================
# Workload data container
# ==========================================================

@dataclass
class DoctorWorkload:
    total_hours: float = 0.0
    total_shifts: int = 0
    night_shifts: int = 0
    weekend_shifts: int = 0

    consecutive_days: int = 0
    consecutive_nights: int = 0

    rest_violations: int = 0

    burnout_score: float = 0.0


# ==========================================================
# Helper functions
# ==========================================================

def _hours_between(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 3600


def _date_key(dt: datetime) -> str:
    """Convert datetime to YYYY-MM-DD string."""
    return dt.date().isoformat()


# ==========================================================
# MAIN ANALYSIS FUNCTION
# ==========================================================

def analyze_workload(
    doctors: List[Doctor],
    shifts: List[Shift],
    assignments: List[Assignment],
    rest_hours_required: int = 18,
) -> Dict[str, DoctorWorkload]:
    """
    Analyze total shifts, hours, night/weekend load, rest violations,
    consecutive days/nights, and burnout score per doctor.
    """

    workload = {doc.id: DoctorWorkload() for doc in doctors}

    # Build shift lookup
    shift_map = {s.id: s for s in shifts}

    # Group assignments per doctor
    doctor_assignments: Dict[str, List[Assignment]] = {doc.id: [] for doc in doctors}
    for a in assignments:
        if a.doctor_id in doctor_assignments:
            doctor_assignments[a.doctor_id].append(a)

    # Analyze each doctor individually
    for doc in doctors:
        w = workload[doc.id]
        assigned = doctor_assignments[doc.id]

        # Sort shifts chronologically
        assigned.sort(key=lambda a: shift_map[a.shift_id].start)

        # Used to compute consecutive sequences
        last_shift_end = None
        last_shift_date = None
        day_streak = 0
        night_streak = 0

        for a in assigned:
            s = shift_map[a.shift_id]
            hours = _hours_between(s.start, s.end)

            # Basic counts
            w.total_hours += hours
            w.total_shifts += 1

            if s.is_night:
                w.night_shifts += 1
            if s.is_weekend:
                w.weekend_shifts += 1

            # ------ Rest violation ------
            if last_shift_end is not None:
                hours_rest = _hours_between(last_shift_end, s.start)
                if hours_rest < rest_hours_required:
                    w.rest_violations += 1

            # ------ Consecutive days / nights ------
            shift_day = _date_key(s.start)

            if last_shift_date == shift_day:
                # Same day → does not count as new consecutive day
                pass
            else:
                # New day:
                if last_shift_date is None:
                    day_streak = 1
                else:
                    prev_date = datetime.fromisoformat(last_shift_date)
                    curr_date = s.start.date()
                    if curr_date == (prev_date + timedelta(days=1)):
                        day_streak += 1
                    else:
                        day_streak = 1

            # Track night streak separately
            if s.is_night:
                night_streak += 1
            else:
                night_streak = 0

            # Store for next iteration
            last_shift_end = s.end
            last_shift_date = shift_day

            # Update worst-case streak observed
            w.consecutive_days = max(w.consecutive_days, day_streak)
            w.consecutive_nights = max(w.consecutive_nights, night_streak)

        # ======================================================
        # Burnout Score Formula
        # ======================================================
        # Normalised components:
        # - Hours load (scaled to 200h)
        # - Night shift load (scaled to 10 nights)
        # - Weekend load (scaled to 8 weekends)
        # - Rest violations
        # - Consecutive days
        # - Consecutive nights
        # ======================================================

        hours_factor = min(w.total_hours / 200.0, 1.0) * 40
        night_factor = min(w.night_shifts / 10.0, 1.0) * 20
        weekend_factor = min(w.weekend_shifts / 8.0, 1.0) * 10
        rest_factor = min(w.rest_violations / 5.0, 1.0) * 10
        consec_days_factor = min(w.consecutive_days / 10.0, 1.0) * 10
        consec_nights_factor = min(w.consecutive_nights / 4.0, 1.0) * 10

        w.burnout_score = (
            hours_factor
            + night_factor
            + weekend_factor
            + rest_factor
            + consec_days_factor
            + consec_nights_factor
        )

    return workload
