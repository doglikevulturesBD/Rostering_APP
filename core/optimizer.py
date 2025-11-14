# core/optimizer.py

from typing import List, Dict, Tuple
from datetime import datetime, date

import pulp

from core.models import Doctor, Shift, Assignment, Roster


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _hours_between(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 3600.0


def _build_leave_map(leave_rows) -> Dict[str, List[Tuple[date, date]]]:
    """
    Convert DB leave rows into:
        doctor_id -> list of (start_date, end_date) as date objects.
    """
    leave_map: Dict[str, List[Tuple[date, date]]] = {}
    if not leave_rows:
        return leave_map

    for row in leave_rows:
        # row is sqlite Row or dict-like
        doc_id = row["doctor_external_id"]
        start = datetime.fromisoformat(row["start_date"]).date()
        end = datetime.fromisoformat(row["end_date"]).date()
        leave_map.setdefault(doc_id, []).append((start, end))

    return leave_map


def _build_conflict_pairs(shifts: List[Shift], rest_hours_required: float) -> List[Tuple[int, int]]:
    """
    Precompute shift index pairs (i, j) that conflict for a *single doctor*,
    either because:
      - The times overlap, OR
      - The rest between them is below rest_hours_required.
    """
    conflict_pairs: List[Tuple[int, int]] = []

    n = len(shifts)
    for i in range(n):
        for j in range(i + 1, n):
            s1 = shifts[i]
            s2 = shifts[j]

            # Overlap if neither ends before the other starts
            overlapping = not (s1.end <= s2.start or s2.end <= s1.start)

            insufficient_rest = False

            # rest from s1 to s2
            if s1.end <= s2.start:
                rest_12 = _hours_between(s1.end, s2.start)
                if rest_12 < rest_hours_required:
                    insufficient_rest = True

            # rest from s2 to s1
            if s2.end <= s1.start:
                rest_21 = _hours_between(s2.end, s1.start)
                if rest_21 < rest_hours_required:
                    insufficient_rest = True

            if overlapping or insufficient_rest:
                conflict_pairs.append((i, j))

    return conflict_pairs


# ---------------------------------------------------------
# MAIN OPTIMISER (hard constraints only)
# ---------------------------------------------------------

def generate_optimized_roster(
    doctors: List[Doctor],
    shifts: List[Shift],
    leave_rows=None,
    rest_hours_required: float = 18.0,
) -> Roster:
    """
    Build an optimised roster using PuLP (MILP) with *hard constraints only*.

    Hard constraints enforced:
      - Each shift has between min_doctors and max_doctors assigned
      - A doctor cannot work overlapping shifts
      - A doctor must have at least rest_hours_required hours between shifts
      - A doctor cannot work on leave days
      - A doctor must have between min_shifts_per_month and max_shifts_per_month

    No soft constraints or fairness yet (Phase 2).
    """

    if not doctors or not shifts:
        # Nothing to optimise
        return Roster(doctors=doctors, shifts=shifts, assignments=[])

    # Index maps for convenience
    doctor_index = {d.id: i for i, d in enumerate(doctors)}
    shift_index = {s.id: j for j, s in enumerate(shifts)}

    num_doctors = len(doctors)
    num_shifts = len(shifts)

    # Leave map
    leave_map = _build_leave_map(leave_rows or [])

    # Conflicting shift pairs (for any single doctor)
    conflict_pairs = _build_conflict_pairs(shifts, rest_hours_required)

    # -------------------------------------------------
    # Model
    # -------------------------------------------------
    model = pulp.LpProblem("ED_Roster_Optimisation", pulp.LpMinimize)

    # Decision variables: x[d, s] = 1 if doctor d works shift s
    x: Dict[Tuple[int, int], pulp.LpVariable] = {}
    for d_idx in range(num_doctors):
        for s_idx in range(num_shifts):
            doc_id = doctors[d_idx].id
            shift_id = shifts[s_idx].id
            x[(d_idx, s_idx)] = pulp.LpVariable(
                f"x_{doc_id}_{shift_id}", lowBound=0, upBound=1, cat=pulp.LpBinary
            )

    # -------------------------------------------------
    # 1. Shift staffing constraints (min / max doctors)
    # -------------------------------------------------
    for s_idx, sh in enumerate(shifts):
        assigned = [x[(d_idx, s_idx)] for d_idx in range(num_doctors)]
        if sh.min_doctors is not None:
            model += (
                pulp.lpSum(assigned) >= sh.min_doctors,
                f"shift_{sh.id}_min_staff",
            )
        if sh.max_doctors is not None:
            model += (
                pulp.lpSum(assigned) <= sh.max_doctors,
                f"shift_{sh.id}_max_staff",
            )

    # -------------------------------------------------
    # 2. Doctor shift-count constraints (min / max per month)
    # -------------------------------------------------
    for d_idx, doc in enumerate(doctors):
        doc_assignments = [x[(d_idx, s_idx)] for s_idx in range(num_shifts)]

        if getattr(doc, "min_shifts_per_month", None) is not None:
            model += (
                pulp.lpSum(doc_assignments) >= doc.min_shifts_per_month,
                f"doctor_{doc.id}_min_shifts",
            )

        if getattr(doc, "max_shifts_per_month", None) is not None:
            model += (
                pulp.lpSum(doc_assignments) <= doc.max_shifts_per_month,
                f"doctor_{doc.id}_max_shifts",
            )

    # -------------------------------------------------
    # 3. Conflict constraints (overlaps + insufficient rest)
    # -------------------------------------------------
    for d_idx, doc in enumerate(doctors):
        for (i, j) in conflict_pairs:
            model += (
                x[(d_idx, i)] + x[(d_idx, j)] <= 1,
                f"conflict_{doc.id}_s{i}_s{j}",
            )

    # -------------------------------------------------
    # 4. Leave constraints (no shifts during leave periods)
    # -------------------------------------------------
    for d_idx, doc in enumerate(doctors):
        doc_id = doc.id
        leave_periods = leave_map.get(doc_id, [])
        if not leave_periods:
            continue

        for s_idx, sh in enumerate(shifts):
            shift_day = sh.start.date()
            # If shift_day falls in any leave period, forbid assignment
            for (lv_start, lv_end) in leave_periods:
                if lv_start <= shift_day <= lv_end:
                    model += (
                        x[(d_idx, s_idx)] == 0,
                        f"leave_{doc_id}_shift_{sh.id}",
                    )
                    break  # no need to check more periods for this shift

    # -------------------------------------------------
    # Objective: Just find *any* feasible solution for now.
    # (Phase 2 will add fairness + burnout minimisation)
    # -------------------------------------------------
    model += 0, "DummyObjective"

    # -------------------------------------------------
    # Solve
    # -------------------------------------------------
    solver = pulp.PULP_CBC_CMD(msg=False)
    result_status = model.solve(solver)

    if pulp.LpStatus[result_status] not in ("Optimal", "Feasible"):
        raise RuntimeError(
            f"No feasible roster found. Solver status: {pulp.LpStatus[result_status]}"
        )

    # -------------------------------------------------
    # Build assignments from solution
    # -------------------------------------------------
    assignments: List[Assignment] = []

    for d_idx, doc in enumerate(doctors):
        for s_idx, sh in enumerate(shifts):
            val = x[(d_idx, s_idx)].value()
            if val is not None and val > 0.5:
                assignments.append(
                    Assignment(
                        doctor_id=doc.id,
                        shift_id=sh.id,
                    )
                )

    return Roster(
        doctors=doctors,
        shifts=shifts,
        assignments=assignments,
    )
