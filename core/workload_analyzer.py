# core/workload_analyzer.py

from datetime import timedelta
from typing import Dict, List
from core.models import Doctor, Shift, Assignment


# default rest rule in hours (can be made configurable later)
REST_REQUIRED_HOURS = 18


class DoctorWorkload:
    """
    Summary metrics for each doctor after roster generation.
    """

    def __init__(self):
        self.total_shifts = 0
        self.total_hours = 0.0
        self.night_shifts = 0
        self.weekend_shifts = 0
        self.consecutive_days = 0
        self.consecutive_nights = 0
        self.intensity_sum = 0
        self.last_shift_end = None

        # Rule-related
        self.rest_violations = 0
        self.rule_flags = []  # list of text warnings

        # Burnout
        self.burnout_score = 0.0


def calculate_burnout(intensity_sum: int, night_shifts: int,
                      consecutive_nights: int, total_hours: float) -> float:
    """
    Simple burnout model:
    - intensity_sum: base fatigue from shift difficulty
    - night_shifts: weighted higher
    - consecutive_nights: penalised heavily
    - total_hours: overall load
    Outputs a score roughly 0–100 (clamped).
    """

    score = (
        intensity_sum * 1.0 +
        night_shifts * 2.0 +
        consecutive_nights * 4.0 +
        (total_hours / 10.0)  # each 10h adds 1 point
    )

    return min(100.0, round(score, 1))


def analyze_workload(
    doctors: List[Doctor],
    shifts: List[Shift],
    assignments: List[Assignment],
) -> Dict[str, DoctorWorkload]:
    """
    Computes workload summary for each doctor.

    Returns:
        workload: dict of doctor_id -> DoctorWorkload
    """

    # Lookups
    shift_map = {s.id: s for s in shifts}
    doctor_ids = {d.id for d in doctors}

    workload: Dict[str, DoctorWorkload] = {
        d.id: DoctorWorkload() for d in doctors
    }

    # Group shifts by doctor
    assignments_by_doctor: Dict[str, List[Shift]] = {d: [] for d in doctor_ids}

    for a in assignments:
        if a.doctor_id in doctor_ids and a.shift_id in shift_map:
            assignments_by_doctor[a.doctor_id].append(shift_map[a.shift_id])

    # Sort shifts by time and compute metrics
    for doc_id, shift_list in assignments_by_doctor.items():
        w = workload[doc_id]

        shift_list.sort(key=lambda s: s.start)

        prev_shift = None
        day_streak = 0
        night_streak = 0

        for shift in shift_list:
            # ---- Basic counts ----
            w.total_shifts += 1
            duration = shift.end - shift.start
            hours = duration.total_seconds() / 3600.0
            w.total_hours += hours

            if shift.is_night:
                w.night_shifts += 1
            if shift.is_weekend:
                w.weekend_shifts += 1

            w.intensity_sum += shift.intensity

            # ---- Rest period violations ----
            if prev_shift:
                rest = (shift.start - prev_shift.end).total_seconds() / 3600.0
                if rest < REST_REQUIRED_HOURS:
                    w.rest_violations += 1
                    w.rule_flags.append(
                        f"Rest violation: only {round(rest, 1)}h between shifts "
                        f"ending {prev_shift.end} and starting {shift.start}"
                    )

            # ---- Consecutive streaks ----
            if prev_shift:
                if shift.is_night and prev_shift.is_night:
                    night_streak += 1
                elif not shift.is_night and not prev_shift.is_night:
                    day_streak += 1
                else:
                    day_streak = 0
                    night_streak = 0

            w.consecutive_days = max(w.consecutive_days, day_streak)
            w.consecutive_nights = max(w.consecutive_nights, night_streak)

            prev_shift = shift

        if shift_list:
            w.last_shift_end = shift_list[-1].end

        # ---- Burnout score ----
        w.burnout_score = calculate_burnout(
            w.intensity_sum,
            w.night_shifts,
            w.consecutive_nights,
            w.total_hours,
        )

    return workload
