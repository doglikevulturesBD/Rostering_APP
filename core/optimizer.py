import pulp
from datetime import datetime

from core.models import Assignment, AssignmentResult


def shifts_overlap(start1, end1, start2, end2):
    """Returns True if two shifts overlap."""
    return not (end1 <= start2 or end2 <= start1)


def build_and_solve_roster(doctors, shifts):
    """
    Basic PuLP optimizer:
    - Satisfies minimum doctors per shift
    - Ensures no overlapping shifts for a doctor
    - Balances total shift count per doctor
    """

    doctor_ids = [doc.id for doc in doctors]
    shift_ids = [sh.id for sh in shifts]

    # Build quick lookups
    idx_doc = {doc.id: i for i, doc in enumerate(doctors)}
    idx_shift = {sh.id: i for i, sh in enumerate(shifts)}

    # --------------------------------------------------------
    # 1) CREATE MODEL
    # --------------------------------------------------------
    model = pulp.LpProblem("Doctor_Roster", pulp.LpMinimize)

    # x[d][s] = 1 if doctor d works shift s
    x = pulp.LpVariable.dicts(
        "assign",
        ((d, s) for d in doctor_ids for s in shift_ids),
        cat=pulp.LpBinary,
    )

    # --------------------------------------------------------
    # 2) HARD CONSTRAINT: MIN DOCTORS PER SHIFT
    # --------------------------------------------------------
    for sh in shifts:
        model += (
            sum(x[(d.id, sh.id)] for d in doctors)
            >= sh.min_doctors,
            f"MinDoctors_Shift_{sh.id}",
        )

    # --------------------------------------------------------
    # 3) HARD CONSTRAINT: NO OVERLAPPING SHIFTS PER DOCTOR
    # --------------------------------------------------------
    for d in doctors:
        for sh1 in shifts:
            for sh2 in shifts:
                if sh1.id >= sh2.id:
                    continue
                if shifts_overlap(sh1.start, sh1.end, sh2.start, sh2.end):
                    model += (
                        x[(d.id, sh1.id)] + x[(d.id, sh2.id)] <= 1,
                        f"NoOverlap_{d.id}_{sh1.id}_{sh2.id}",
                    )

    # --------------------------------------------------------
    # 4) OBJECTIVE: FAIRNESS (spread shifts evenly)
    # --------------------------------------------------------
    total_shifts = {
        d.id: pulp.lpSum([x[(d.id, sh.id)] for sh in shifts]) for d in doctors
    }

    # Minimize difference between max & min allocated shifts
    max_shifts = pulp.LpVariable("max_shifts", lowBound=0)
    min_shifts = pulp.LpVariable("min_shifts", lowBound=0)

    for d in doctors:
        model += total_shifts[d.id] <= max_shifts
        model += total_shifts[d.id] >= min_shifts

    # Objective: minimise spread
    model += max_shifts - min_shifts

    # --------------------------------------------------------
    # 5) SOLVE
    # --------------------------------------------------------
    solver = pulp.PULP_CBC_CMD(msg=False)
    result = model.solve(solver)

    if pulp.LpStatus[result] not in ("Optimal", "Feasible"):
        return None

    # --------------------------------------------------------
    # 6) BUILD OUTPUT
    # --------------------------------------------------------
    assignments = []

    for d in doctors:
        for sh in shifts:
            if pulp.value(x[(d.id, sh.id)]) == 1:
                assignments.append(
                    Assignment(
                        doctor_id=d.id,
                        shift_id=sh.id,
                        shift_start=sh.start.isoformat(),
                        shift_end=sh.end.isoformat(),
                    )
                )

    return AssignmentResult(assignments=assignments)

