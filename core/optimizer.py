import pulp
from datetime import timedelta

from core.models import Assignment, AssignmentResult, Shift, Doctor
from core.database import get_all_leave


REST_HOURS = 11  # minimum rest period between shifts


def shifts_overlap(start1, end1, start2, end2) -> bool:
    """
    Returns True if two shifts overlap in time.
    """
    return not (end1 <= start2 or end2 <= start1)


def build_and_solve_roster(doctors: list[Doctor], shifts: list[Shift]) -> AssignmentResult | None:
    """
    Phase 2 optimiser (PuLP-based):

    Hard constraints:
      1. Min & max doctors per shift
      2. No overlapping shifts per doctor
      3. At least REST_HOURS between any two shifts for a doctor
      4. Per-doctor monthly min & max shifts from doctor profile
      5. Respect leave (no shifts during leave periods)

    Objective:
      - Minimise difference between most- and least-worked doctors
        in terms of number of shifts (fairness).

    Returns:
      AssignmentResult(assignments=[Assignment(...), ...])
      or None if infeasible.
    """

    if not doctors or not shifts:
        return None

    doctor_ids = [d.id for d in doctors]
    shift_ids = [s.id for s in shifts]

    # Quick lookup maps
    doctor_by_id = {d.id: d for d in doctors}
    shift_by_id = {s.id: s for s in shifts}

    # --------------------------------------------------------
    # CREATE MODEL
    # --------------------------------------------------------
    model = pulp.LpProblem("Doctor_Roster", pulp.LpMinimize)

    # x[d, s] = 1 if doctor d works shift s
    x = pulp.LpVariable.dicts(
        "assign",
        ((d_id, s_id) for d_id in doctor_ids for s_id in shift_ids),
        cat=pulp.LpBinary,
    )

    # --------------------------------------------------------
    # 1) MIN & MAX DOCTORS PER SHIFT
    # --------------------------------------------------------
    for s in shifts:
        model += (
            pulp.lpSum(x[(d_id, s.id)] for d_id in doctor_ids)
            >= s.min_doctors,
            f"MinDoctors_Shift_{s.id}",
        )
        model += (
            pulp.lpSum(x[(d_id, s.id)] for d_id in doctor_ids)
            <= s.max_doctors,
            f"MaxDoctors_Shift_{s.id}",
        )

    # --------------------------------------------------------
    # 2) NO OVERLAPPING SHIFTS + 3) REST PERIOD >= REST_HOURS
    #    (We enforce both simultaneously)
    # --------------------------------------------------------
    rest_delta = timedelta(hours=REST_HOURS)

    for d_id in doctor_ids:
        for i, s1 in enumerate(shifts):
            for j, s2 in enumerate(shifts):
                if j <= i:
                    continue

                # Condition 1: direct overlap in time
                overlap = shifts_overlap(s1.start, s1.end, s2.start, s2.end)

                # Condition 2: rest window violation
                # If s2 starts before s1.end + REST_HOURS, they can't both be worked
                rest_violation = (
                    s2.start < s1.end + rest_delta
                    and s2.start >= s1.start  # s2 after s1 begins
                )

                # Also check opposite direction (s1 after s2)
                rest_violation_reverse = (
                    s1.start < s2.end + rest_delta
                    and s1.start >= s2.start
                )

                if overlap or rest_violation or rest_violation_reverse:
                    model += (
                        x[(d_id, s1.id)] + x[(d_id, s2.id)] <= 1,
                        f"NoOverlapOrRest_{d_id}_{s1.id}_{s2.id}",
                    )

    # --------------------------------------------------------
    # 4) PER-DOCTOR MIN & MAX SHIFTS (MONTH)
    # --------------------------------------------------------
    for d in doctors:
        total_shifts_for_d = pulp.lpSum(x[(d.id, s.id)] for s in shifts)

        # Only enforce if min/max are >0 to avoid weird legacy values
        if d.min_shifts_per_month > 0:
            model += (
                total_shifts_for_d >= d.min_shifts_per_month,
                f"MinShifts_Doctor_{d.id}",
            )
        if d.max_shifts_per_month > 0:
            model += (
                total_shifts_for_d <= d.max_shifts_per_month,
                f"MaxShifts_Doctor_{d.id}",
            )

    # --------------------------------------------------------
    # 5) LEAVE CONSTRAINTS
    # --------------------------------------------------------
    # leave_requests table:
    #   doctor_external_id, start_date (YYYY-MM-DD), end_date (YYYY-MM-DD)
    leave_rows = get_all_leave()

    # Convert leave into a map doctor_id -> list of (start_date, end_date)
    leave_map: dict[str, list[tuple]] = {}
    for row in leave_rows:
        doc_id = row["doctor_external_id"]
        if doc_id not in doctor_by_id:
            # Leave for doctor not in this run (ignore)
            continue

        start_date = row["start_date"]
        end_date = row["end_date"]
        leave_map.setdefault(doc_id, []).append((start_date, end_date))

    # Apply leave: if a shift date lies within a doctor's leave window,
    # x[d, s] must be 0.
    for d_id, intervals in leave_map.items():
        for s in shifts:
            shift_date_str = s.start.date().isoformat()
            for (start_str, end_str) in intervals:
                if start_str <= shift_date_str <= end_str:
                    model += (
                        x[(d_id, s.id)] == 0,
                        f"Leave_{d_id}_{s.id}_{start_str}_{end_str}",
                    )
                    break  # no need to check other intervals for this shift

    # --------------------------------------------------------
    # OBJECTIVE: FAIRNESS IN SHIFT COUNT
    # --------------------------------------------------------
    total_shifts = {
        d.id: pulp.lpSum(x[(d.id, s.id)] for s in shifts) for d in doctors
    }

    max_shifts = pulp.LpVariable("max_shifts_per_doctor", lowBound=0)
    min_shifts = pulp.LpVariable("min_shifts_per_doctor", lowBound=0)

    for d in doctors:
        model += total_shifts[d.id] <= max_shifts
        model += total_shifts[d.id] >= min_shifts

    # Minimize spread between most and least loaded doctors
    model += max_shifts - min_shifts

    # --------------------------------------------------------
    # SOLVE
    # --------------------------------------------------------
    solver = pulp.PULP_CBC_CMD(msg=False)
    status = model.solve(solver)

    if pulp.LpStatus[status] not in ("Optimal", "Feasible"):
        # No feasible solution under current constraints
        return None

    # --------------------------------------------------------
    # BUILD RESULT
    # --------------------------------------------------------
    assignments: list[Assignment] = []

    for d_id in doctor_ids:
        for s in shifts:
            val = pulp.value(x[(d_id, s.id)])
            if val is not None and val > 0.5:
                assignments.append(
                    Assignment(
                        doctor_id=d_id,
                        shift_id=s.id,
                        shift_start=s.start,
                        shift_end=s.end,
                    )
                )

    return AssignmentResult(assignments=assignments)

