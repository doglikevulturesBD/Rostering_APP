# core/feasibility.py

from typing import List, Dict, Any
from datetime import datetime, date

from core.models import Doctor, Shift
from core.optimizer import _build_leave_map  # reuse helper


def analyze_feasibility(
    doctors: List[Doctor],
    shifts: List[Shift],
    leave_rows=None,
) -> Dict[str, Any]:
    """
    Simple feasibility analysis:
      - total required doctor-shifts vs doctor capacity
      - night & weekend demand
      - leave-related bottlenecks
    Returns a dict with summary numbers and a list of warning strings.
    """
    result: Dict[str, Any] = {}
    warnings = []

    if not doctors or not shifts:
        result["feasible"] = False
        warnings.append("No doctors or no shifts defined.")
        result["warnings"] = warnings
        return result

    # Basic totals
    total_min_demand = sum(s.min_doctors for s in shifts)
    total_max_demand = sum(s.max_doctors for s in shifts)

    total_min_capacity = sum(d.min_shifts_per_month for d in doctors)
    total_max_capacity = sum(d.max_shifts_per_month for d in doctors)

    night_shifts = [s for s in shifts if s.start.hour >= 21]
    weekend_shifts = [s for s in shifts if s.is_weekend]

    result["total_min_demand"] = total_min_demand
    result["total_max_demand"] = total_max_demand
    result["total_min_capacity"] = total_min_capacity
    result["total_max_capacity"] = total_max_capacity
    result["night_shift_demand"] = sum(s.min_doctors for s in night_shifts)
    result["weekend_shift_demand"] = sum(s.min_doctors for s in weekend_shifts)
    result["num_doctors"] = len(doctors)

    # Overall feasibility check
    if total_min_demand > total_max_capacity:
        warnings.append(
            f"Total minimum staffing requirement ({total_min_demand}) "
            f"exceeds doctors' maximum capacity ({total_max_capacity})."
        )

    if total_max_demand < total_min_capacity:
        warnings.append(
            f"Doctors' minimum shifts ({total_min_capacity}) may exceed "
            f"the demand's upper bound ({total_max_demand}). "
            f"Some doctors may not reach their min_shifts."
        )

    # Leave-based bottlenecks
    leave_map = _build_leave_map(leave_rows or [])

    # For each shift, check how many docs are actually available
    per_shift_issues = []
    for s in shifts:
        shift_day = s.start.date()
        available = 0
        for d in doctors:
            periods = leave_map.get(d.id, [])
            on_leave = False
            for (lv_start, lv_end) in periods:
                if lv_start <= shift_day <= lv_end:
                    on_leave = True
                    break
            if not on_leave:
                available += 1

        if available < s.min_doctors:
            per_shift_issues.append(
                f"{shift_day} {s.start.strftime('%H:%M')}–{s.end.strftime('%H:%M')}: "
                f"needs {s.min_doctors} doctors, only {available} available (due to leave)."
            )

    if per_shift_issues:
        warnings.append("Leave-related coverage issues detected:")
        warnings.extend(per_shift_issues)

    result["warnings"] = warnings
    # "Feasible" here means no obvious global impossibility
    result["feasible"] = (total_min_demand <= total_max_capacity) and (len(per_shift_issues) == 0)

    return result

