# core/workload_analyzer.py

from typing import Dict, List
from datetime import datetime

from core.models import Doctor, Shift, Assignment, DoctorWorkload


def analyze_workload(
    doctors: List[Doctor],
    shifts: List[Shift],
    assignments: List[Assignment],
) -> Dict[str, DoctorWorkload]:
    """Compute simple workload & burnout stats for each doctor."""

    shift_by_id = {s.id: s for s in shifts}
    workload: Dict[str, DoctorWorkload] = {
        d.id: DoctorWorkload(doctor_id=d.id) for d in doctors
    }

    # Group assignments per doctor
    doc_assignments: Dict[str, List[Shift]] = {d.id: [] for d in doctors}
    for a in assignments:
        sh = shift_by_id.get(a.shift_id)
        if sh:
            doc_assignments[a.doctor_id].append(sh)

    for doc in doctors:
        wid = doc.id
        w = workload[wid]
        assigned_shifts = sorted(doc_assignments[wid], key=lambda s: s.start)

        if not assigned_shifts:
            continue

        w.total_shifts = len(assigned_shifts)
        w.total_hours = sum(s.duration_hours for s in assigned_shifts)
        w.night_shifts = sum(1 for s in assigned_shifts if s.start.hour >= 21)
        w.weekend_shifts = sum(1 for s in assigned_shifts if s.is_weekend)

        # Consecutive days worked
        dates = sorted({s.start.date() for s in assigned_shifts})
        consec = 1
        max_consec = 1
        for i in range(1, len(dates)):
            if (dates[i] - dates[i - 1]).days == 1:
                consec += 1
                max_consec = max(max_consec, consec)
            else:
                consec = 1
        w.consecutive_days = max_consec

        # Consecutive nights
        night_dates = sorted({s.start.date() for s in assigned_shifts if s.start.hour >= 21})
        consec_n = 1
        max_consec_n = 1
        if night_dates:
            for i in range(1, len(night_dates)):
                if (night_dates[i] - night_dates[i - 1]).days == 1:
                    consec_n += 1
                    max_consec_n = max(max_consec_n, consec_n)
                else:
                    consec_n = 1
        else:
            max_consec_n = 0
        w.consecutive_nights = max_consec_n

        # Rest violations (< 11 hours between shifts)
        rest_violations = 0
        for i in range(len(assigned_shifts) - 1):
            s1 = assigned_shifts[i]
            s2 = assigned_shifts[i + 1]
            gap_hours = (s2.start - s1.end).total_seconds() / 3600.0
            if gap_hours < 11:
                rest_violations += 1
        w.rest_violations = rest_violations

        # Very simple burnout score
        # You can refine later
        w.burnout_score = (
            w.total_hours / 10.0
            + w.night_shifts * 2.0
            + w.weekend_shifts * 1.5
            + max(0, w.consecutive_nights - 2) * 3.0
            + w.rest_violations * 5.0
        )

    return workload

