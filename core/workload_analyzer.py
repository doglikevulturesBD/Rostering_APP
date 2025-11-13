# core/workload_analyzer.py

from datetime import timedelta
from typing import Dict, List
from core.models import Doctor, Shift, Assignment


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
        self.rule_flags = []  # will store violations later


def analyze_workload(doctors: List[Doctor], shifts: List[Shift], assignments: List[Assignment]):
    """
    Computes workload summary for each doctor.
    Returns a dict: { doctor_id : DoctorWorkload }
    """

    # Build lookup tables
    shift_map = {s.id: s for s in shifts}
    doctor_ids = {d.id for d in doctors}

    # Initialize workload dict
    workload: Dict[str, DoctorWorkload] = {d.id: DoctorWorkload() for d in doctors}

    # Group assignments by doctor
    assignments_by_doctor: Dict[str, List[Shift]] = {d: [] for d in doctor_ids}

    for a in assignments:
        if a.doctor_id in doctor_ids and a.shift_id in shift_map:
            assignments_by_doctor[a.doctor_id].append(shift_map[a.shift_id])

    # Sort shifts for each doctor by start time
    for doc in doctor_ids:
        assignments_by_doctor[doc].sort(key=lambda s: s.start)

    # Compute metrics
    for doc_id, shift_list in assignments_by_doctor.items():
        w = workload[doc_id]

        prev_shift = None
        day_streak = 0
        night_streak = 0

        for shift in shift_list:

            # (1) Total shifts
            w.total_shifts += 1

            # (2) Total hours
            duration = shift.end - shift.start
            w.total_hours += duration.total_seconds() / 3600.0

            # (3) Night shifts
            if shift.is_night:
                w.night_shifts += 1

            # (4) Weekend shifts
            if shift.is_weekend:
                w.weekend_shifts += 1

            # (5) Intensity (for burnout)
            w.intensity_sum += shift.intensity

            # (6) Consecutive day/night streaks
            if prev_shift:
                rest_hours = (shift.start - prev_shift.end).total_seconds() / 3600.0

                if shift.is_night and prev_shift.is_night:
                    night_streak += 1
                elif not shift.is_night and not prev_shift.is_night:
                    day_streak += 1
                else:
                    day_streak = 0
                    night_streak = 0

                # Store longest streak
                w.consecutive_days = max(w.consecutive_days, day_streak)
                w.consecutive_nights = max(w.consecutive_nights, night_streak)

            prev_shift = shift

        # Save last shift end
        if shift_list:
            w.last_shift_end = shift_list[-1].end

    return workload
