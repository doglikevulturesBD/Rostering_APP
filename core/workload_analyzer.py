# core/workload_analyzer.py
from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime, timedelta

from core.models import Doctor, Shift, Assignment


@dataclass
class WorkloadSummary:
    doctor_id: str
    total_shifts: int
    total_hours: float
    night_shifts: int
    weekend_shifts: int
    consecutive_days: int
    consecutive_nights: int
    rest_violations: int
    burnout_score: float


def analyze_workload(doctors: List[Doctor], shifts: List[Shift], assignments: List[Assignment]):
    # Map shift_id → shift
    shift_map = {s.id: s for s in shifts}

    # Group assignments by doctor
    doc_assignments: Dict[str, List[Shift]] = {d.id: [] for d in doctors}
    for a in assignments:
        doc_assignments[a.doctor_id].append(shift_map[a.shift_id])

    workload: Dict[str, WorkloadSummary] = {}

    # Average hours across doctors (for fairness factor)
    hours_per_doc = []

    # First pass – compute raw stats
    temp_stats = {}
    for d in doctors:
        assigned = sorted(doc_assignments[d.id], key=lambda s: s.start)

        total_hours = sum(s.duration_hours for s in assigned)
        hours_per_doc.append(total_hours)

        night_shifts = sum(1 for s in assigned if s.start.hour >= 21)
        weekend_shifts = sum(1 for s in assigned if s.is_weekend)

        # sequential counting:
        consec_days = _compute_consecutive_days(assigned)
        consec_nights = _compute_consecutive_nights(assigned)

        # rest violations
        rv = _compute_rest_violations(assigned)

        temp_stats[d.id] = {
            "assigned": assigned,
            "hours": total_hours,
            "nights": night_shifts,
            "weekends": weekend_shifts,
            "consec_days": consec_days,
            "consec_nights": consec_nights,
            "rest_violations": rv,
        }

    avg_hours = sum(hours_per_doc) / len(hours_per_doc) if hours_per_doc else 0

    # Second pass – burnout scoring
    for d in doctors:
        st = temp_stats[d.id]
        burnout = _compute_burnout_score(
            hours=st["hours"],
            contract_hours=d.contract_hours_per_month,
            night_shifts=st["nights"],
            weekend_shifts=st["weekends"],
            consecutive_days=st["consec_days"],
            consecutive_nights=st["consec_nights"],
            rest_violations=st["rest_violations"],
            avg_hours=avg_hours,
        )

        workload[d.id] = WorkloadSummary(
            doctor_id=d.id,
            total_shifts=len(temp_stats[d.id]["assigned"]),
            total_hours=st["hours"],
            night_shifts=st["nights"],
            weekend_shifts=st["weekends"],
            consecutive_days=st["consec_days"],
            consecutive_nights=st["consec_nights"],
            rest_violations=st["rest_violations"],
            burnout_score=burnout,
        )

    return workload


# ------------------------------------------
# Helper functions
# ------------------------------------------

def _compute_consecutive_days(shifts):
    if not shifts:
        return 0

    days = sorted({s.start.date() for s in shifts})
    consec = 1
    best = 1

    for i in range(1, len(days)):
        if (days[i] - days[i - 1]).days == 1:
            consec += 1
            best = max(best, consec)
        else:
            consec = 1
    return best


def _compute_consecutive_nights(shifts):
    nights = [s.start.date() for s in shifts if s.start.hour >= 21]
    nights = sorted(set(nights))
    if not nights:
        return 0

    consec = 1
    best = 1
    for i in range(1, len(nights)):
        if (nights[i] - nights[i - 1]).days == 1:
            consec += 1
            best = max(best, consec)
        else:
            consec = 1
    return best


def _compute_rest_violations(shifts):
    shifts = sorted(shifts, key=lambda s: s.end)
    violations = 0
    for i in range(1, len(shifts)):
        rest = (shifts[i].start - shifts[i - 1].end).total_seconds() / 3600
        if rest < 11:
            violations += 1
    return violations


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def _compute_burnout_score(
    hours,
    contract_hours,
    night_shifts,
    weekend_shifts,
    consecutive_days,
    consecutive_nights,
    rest_violations,
    avg_hours,
):
    # Factor scaling
    hours_factor = clamp((hours / contract_hours) * 100, 0, 100) if contract_hours else 0
    night_factor = clamp(night_shifts * 33, 0, 100)  # 3 nights ~ 100
    weekend_factor = clamp(weekend_shifts * 33, 0, 100)
    consec_days_factor = 100 if consecutive_days >= 6 else \
                         75 if consecutive_days == 5 else \
                         50 if consecutive_days == 4 else \
                         10
    consec_nights_factor = 100 if consecutive_nights >= 3 else \
                           70 if consecutive_nights == 2 else \
                           40 if consecutive_nights == 1 else \
                           10
    rest_factor = min(rest_violations * 25, 100)

    fairness_factor = clamp(abs(hours - avg_hours) * 3, 0, 100)

    score = (
        0.25 * hours_factor
        + 0.20 * night_factor
        + 0.15 * weekend_factor
        + 0.15 * consec_days_factor
        + 0.10 * consec_nights_factor
        + 0.10 * rest_factor
        + 0.05 * fairness_factor
    )

    return round(score, 2)
