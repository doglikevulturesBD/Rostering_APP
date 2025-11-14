# core/optimizer.py

from typing import List, Dict, Tuple
from datetime import datetime, date

import pulp

from core.models import Doctor, Shift, Assignment, Roster


def _hours_between(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 3600.0


def _build_leave_map(leave_rows) -> Dict[str, List[Tuple[date, date]]]:
    leave_map: Dict[str, List[Tuple[date, date]]] = {}
    if not leave_rows:
        return leave_map

    for row in leave_rows:
        doc_id = row["doctor_external_id"]
        start = datetime.fromisoformat(row["start_date"]).date()
        end = datetime.fromisoformat(row["end_date"]).date()
        leave_map.setdefault(doc_id, []).append((start, end))

    return leave_map


def _build_conflict_pairs(shifts: List[Shift], rest_hours_required: float) -> List[Tuple[int, int]]:
    conflict_pairs: List[Tuple[int, int]] = []
    n = len(shifts)

    for i in range(n):
        for j in range(i + 1, n):
            s1 = shifts[i]
            s2 = shifts[j]

            overlapping = not (s1.end <= s2.start or s2.end <= s1.start)
            insufficient_rest = False

            if s1.end <= s2.start:
                rest_12 = _hours_between(s1.end, s2.start)
                if rest_12 < rest_hours_required:
                    insufficient_rest = True

            if s2.end <= s1.start:
                rest_21 = _hours_between(s2.end, s1.start)
                if rest_21 < rest_hours_required:
                    insufficient_rest = True

            if overlapping or insufficient_rest:
                conflict_pairs.append((i, j))

    return conflict_pairs


def generate_optimized_roster(
    doctors: List[Doctor],
    shifts: List[Shift],
    leave_rows=None,
    rest_hours_required: float = 11.0,
) -> Roster:
    """Optimised roster using PuLP (hard constraints only)."""

    if not doctors or not shifts:
        return Roster(doctors=doctors, shifts=shifts, assignments=[])

    num_doctors = len(doctors)
    num_shifts = len(shifts)

    leave_map = _build_leave_map(leave_rows or [])
    conflict_pairs = _build_conflict_pairs(shifts, rest_hours_required)

    model = pulp.LpProblem("ED_Roster_Optimisation", pulp.LpMinimize)

    # Decision vars x[d,s] ∈ {0,1}
    x: Dict[Tuple[int, int], pulp.LpVariable] = {}
    for d_idx in range(num_doctors):
        for s_idx in range(num_shifts):
            x[(d_idx, s_idx)] = pulp.LpVariable(
                f"x_{doctors[d_idx].id}_{shifts[s_idx].id}",
                lowBound=0,
                upBound=1,
                cat=pulp.LpBinary,
            )

    # 1. Shift staffing
    for s_idx, sh in enumerate(shifts):
        assigned = [x[(d_idx, s_idx)] for d_idx in range(num_doctors)]
        if sh.min_doctors is not None:
            model += pulp.lpSum(assigned) >= sh.min_doctors, f"shift_{sh.id}_min"
        if sh.max_doctors is not None:
            model += pulp.lpSum(assigned) <= sh.max_doctors, f"shift_{sh.id}_max"

    # 2. Doctor min/max shifts
    for d_idx, doc in enumerate(doctors):
        doc_x = [x[(d_idx, s_idx)] for s_idx in range(num_shifts)]
        if doc.min_shifts_per_month is not None:
            model += (
                pulp.lpSum(doc_x) >= doc.min_shifts_per_month,
                f"doc_{doc.id}_min",
            )
        if doc.max_shifts_per_month is not None:
            model += (
                pulp.lpSum(doc_x) <= doc.max_shifts_per_month,
                f"doc_{doc.id}_max",
            )

    # 3. Conflicts (overlaps + rest)
    for d_idx, doc in enumerate(doctors):
        for (i, j) in conflict_pairs:
            model += x[(d_idx, i)] + x[(d_idx, j)] <= 1, f"conflict_{doc.id}_{i}_{j}"

    # 4. Leave: no shifts during leave
    for d_idx, doc in enumerate(doctors):
        periods = leave_map.get(doc.id, [])
        if not periods:
            continue

        for s_idx, sh in enumerate(shifts):
            shift_day = sh.start.date()
            for (lv_start, lv_end) in periods:
                if lv_start <= shift_day <= lv_end:
                    model += x[(d_idx, s_idx)] == 0, f"leave_{doc.id}_{sh.id}"
                    break

    # Objective: any feasible solution
    model += 0, "DummyObjective"

    solver = pulp.PULP_CBC_CMD(msg=False)
    result = model.solve(solver)

    if pulp.LpStatus[result] not in ("Optimal", "Feasible"):
        raise RuntimeError(f"No feasible roster. Status: {pulp.LpStatus[result]}")

    assignments: List[Assignment] = []
    for d_idx, doc in enumerate(doctors):
        for s_idx, sh in enumerate(shifts):
            if x[(d_idx, s_idx)].value() > 0.5:
                assignments.append(Assignment(doctor_id=doc.id, shift_id=sh.id))

    return Roster(doctors=doctors, shifts=shifts, assignments=assignments)
