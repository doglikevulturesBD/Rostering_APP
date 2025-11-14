# core/optimizer.py

from typing import List, Dict, Tuple, Optional
from datetime import datetime

from core.models import Doctor, Shift, Assignment, Roster

# OR-Tools CP-SAT
try:
    from ortools.sat.python import cp_model
except ImportError as e:
    raise ImportError(
        "OR-Tools is required for the optimiser. "
        "Install it with: pip install ortools"
    ) from e


def _build_leave_map(leave_rows) -> Dict[str, List[Tuple[datetime, datetime]]]:
    """
    Convert DB leave rows into a mapping:
    doctor_id -> list of (start_date, end_date) as date objects
    """
    leave_map: Dict[str, List[Tuple[datetime, datetime]]] = {}
    if not leave_rows:
        return leave_map

    for row in leave_rows:
        # row is sqlite Row or dict-like
        doctor_id = row["doctor_external_id"]
        start = datetime.fromisoformat(row["start_date"]).date()
        end = datetime.fromisoformat(row["end_date"]).date()

        leave_map.setdefault(doctor_id, []).append((start, end))

    return leave_map


def generate_optimized_roster(
    doctors: List[Doctor],
    shifts: List[Shift],
    leave_rows=None,
    rest_hours_required: int = 18,
) -> Roster:
    """
    Build an optimised roster using OR-Tools CP-SAT.

    Hard constraints:
    - Each shift has between min_doctors and max_doctors assigned
    - A doctor cannot work overlapping shifts
    - A doctor must have at least `rest_hours_required` hours between any two shifts
    - A doctor cannot work on leave days
    - A doctor must be between min_shifts and max_shifts per month
    """

    model = cp_model.CpModel()

    num_doctors = len(doctors)
    num_shifts = len(shifts)

    if num_doctors == 0 or num_shifts == 0:
        # nothing to optimise – return empty roster
        return Roster(doctors=doctors, shifts=shifts, assignments=[])

    # Index maps
    doctor_index = {d.id: i for i, d in enumerate(doctors)}
    shift_index = {s.id: j for j, s in enumerate(shifts)}

    # Leave map: doctor_id -> [(start_date, end_date), ...]
    leave_map = _build_leave_map(leave_rows or [])

    # ----------------------------------------------------
    # Decision variables: x[d, s] = 1 if doctor d works shift s
    # ----------------------------------------------------
    x = {}
    for d_idx, doc in enumerate(doctors):
        for s_idx, sh in enumerate(shifts):
            x[(d_idx, s_idx)] = model.NewBoolVar(f"x_{doc.id}_{sh.id}")

    # ----------------------------------------------------
    # 1. Shift staffing constraints
    #    Sum over doctors for each shift between min_doctors and max_doctors
    # ----------------------------------------------------
    for s_idx, sh in enumerate(shifts):
        assigned = [x[(d_idx, s_idx)] for d_idx in range(num_doctors)]
        if sh.min_doctors is not None:
            model.Add(sum(assigned) >= sh.min_doctors)
        if sh.max_doctors is not None:
            model.Add(sum(assigned) <= sh.max_doctors)

    # ----------------------------------------------------
    # 2. Doctor shift-count constraints (min/max shifts)
    # ----------------------------------------------------
    for d_idx, doc in enumerate(doctors):
        doc_assignments = [x[(d_idx, s_idx)] for s_idx in range(num_shifts)]
        if doc.min_shifts_per_month is not None:
            model.Add(sum(doc_assignments) >= doc.min_shifts_per_month)
        if doc.max_shifts_per_month is not None:
            model.Add(sum(doc_assignments) <= doc.max_shifts_per_month)

    # ----------------------------------------------------
    # Precompute overlap & rest-conflict pairs between shifts
    # ----------------------------------------------------
    conflict_pairs: List[Tuple[int, int]] = []
    for i in range(num_shifts):
        for j in range(i + 1, num_shifts):
            s1 = shifts[i]
            s2 = shifts[j]

            # Time overlap?
            overlapping = not (s1.end <= s2.start or s2.end <= s1.start)

            insufficient_rest = False
            # Rest from s1 to s2
            if s1.end <= s2.start:
                rest_12 = (s2.start - s1.end).total_seconds() / 3600.0
                if rest_12 < rest_hours_required:
                    insufficient_rest = True
            # Rest from s2 to s1
            if s2.end <= s1.start:
                rest_21 = (s1.start - s2.end).total_seconds() / 3600.0
                if rest_21 < rest_hours_required:
                    insufficient_rest = True

            if overlapping or insufficient_rest:
                conflict_pairs.append((i, j))

    # ----------------------------------------------------
    # 3. For each doctor, they cannot take conflicting shift pairs
    # ----------------------------------------------------
    for d_idx in range(num_doctors):
        for (i, j) in conflict_pairs:
            model.Add(x[(d_idx, i)] + x[(d_idx, j)] <= 1)

    # ----------------------------------------------------
    # 4. Leave constraints: no shifts on leave days
    # ----------------------------------------------------
    for d_idx, doc in enumerate(doctors):
        doc_leave_periods = leave_map.get(doc.id, [])
        if not doc_leave_periods:
            continue

        for s_idx, sh in enumerate(shifts):
            shift_day = sh.start.date()
            # If shift_day is inside any leave period -> forbid this assignment
            for (lv_start, lv_end) in doc_leave_periods:
                if lv_start <= shift_day <= lv_end:
                    model.Add(x[(d_idx, s_idx)] == 0)
                    break  # no need to check more leave ranges

    # ----------------------------------------------------
    # (Optional) Objective:
    # For now, we just ask for ANY feasible solution.
    # Later we can minimise burnout, unfairness, etc.
    # ----------------------------------------------------
    # model.Minimize(0)
    # Just solve as satisfaction:
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    solver.parameters.num_search_workers = 8

    result = solver.Solve(model)

    if result not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError("No feasible roster found by the optimiser.")

    # ----------------------------------------------------
    # Build assignments from solution
    # ----------------------------------------------------
    assignments: List[Assignment] = []

    for d_idx, doc in enumerate(doctors):
        for s_idx, sh in enumerate(shifts):
            if solver.Value(x[(d_idx, s_idx)]) == 1:
                assignments.append(
                    Assignment(
                        doctor_id=doc.id,
                        shift_id=sh.id,
                    )
                )

    roster = Roster(
        doctors=doctors,
        shifts=shifts,
        assignments=assignments,
    )

    return roster
