import pulp
from datetime import timedelta
from collections import defaultdict

from core.models import Assignment, AssignmentResult, Shift, Doctor
from core.database import get_all_leave

REST_HOURS = 11  # minimum rest period between shifts


# ----------------- helpers ----------------- #

def shifts_overlap(start1, end1, start2, end2) -> bool:
    """Returns True if two shifts overlap in time."""
    return not (end1 <= start2 or end2 <= start1)


def is_night_shift(shift: Shift) -> bool:
    """
    Night = starts at or after 21:00 OR ends at/before 07:00 (crossing midnight).
    Adjust if your templates change.
    """
    sh = shift.start.hour
    eh = shift.end.hour
    return sh >= 21 or eh <= 7


# ----------------- main solver ----------------- #

def build_and_solve_roster(
    doctors: list[Doctor],
    shifts: list[Shift],
) -> AssignmentResult | None:
    """
    Optimiser (PuLP-based) with hard clinical rules and fairness:

    Hard constraints:
      1. Min & max doctors per shift
      2. No overlapping shifts per doctor
      3. At least REST_HOURS between any two shifts for a doctor
      4. Per-doctor monthly min & max shifts from doctor profile
      5. Respect leave (no shifts during leave periods)
      6. Each doctor works between 1 and 3 weekends per month
         (weekend = any Sat/Sun shift; nights handled separately)
      7. If a doctor works Friday night, they must also work Sat & Sun night (same weekend)
      8. Max 2 weekday night shifts (Mon–Thu) per ISO week
      9. Max 3 nights in a row (no 4 consecutive nights)

    Objective:
      - Minimise spread between most- and least-worked doctors (total shifts)
      - Also minimise spread between most- and least-worked doctors (night shifts)

    Returns:
      AssignmentResult(assignments=[Assignment(...), ...])
      or None if infeasible.
    """

    if not doctors or not shifts:
        return None

    doctor_ids = [d.id for d in doctors]
    shift_ids = [s.id for s in shifts]

    doctor_by_id = {d.id: d for d in doctors}

    # --------------------------------------------------------
    # PRE-COMPUTE STRUCTURES FOR WEEKENDS & NIGHTS
    # --------------------------------------------------------

    # Map: (iso_year, iso_week) -> list of *all* weekend shift IDs (Sat/Sun, any type)
    weekends: dict[tuple[int, int], list[int]] = defaultdict(list)

    # Map: (iso_year, iso_week) -> dict{'fri','sat','sun'} -> night shift id or None
    weekend_nights: dict[tuple[int, int], dict[str, int | None]] = {}

    # Map: (iso_year, iso_week) -> list of night shift IDs that are weekday nights (Mon–Thu)
    weekday_nights_per_week: dict[tuple[int, int], list[int]] = defaultdict(list)

    # For consecutive nights: map date -> night shift id
    night_shift_by_date: dict = {}

    night_shift_ids: list[int] = []

    for s in shifts:
        dt = s.start
        iso_year, iso_week, _ = dt.isocalendar()
        dow = dt.weekday()  # Mon=0 ... Sun=6

        # Weekend shifts: Sat (5), Sun (6) – ANY shift counts for weekend load
        if dow in (5, 6):
            weekends[(iso_year, iso_week)].append(s.id)

        # Night shift logic
        if is_night_shift(s):
            night_shift_ids.append(s.id)
            date_key = s.start.date()
            night_shift_by_date[date_key] = s.id

            # Weekend nights - for F/S/S block rule
            if dow in (4, 5, 6):  # Fri=4, Sat=5, Sun=6
                wn = weekend_nights.setdefault(
                    (iso_year, iso_week),
                    {"fri": None, "sat": None, "sun": None},
                )
                if dow == 4:
                    wn["fri"] = s.id
                elif dow == 5:
                    wn["sat"] = s.id
                else:
                    wn["sun"] = s.id

            # Weekday nights (Mon–Thu) per week for limit=2
            if dow in (0, 1, 2, 3):
                weekday_nights_per_week[(iso_year, iso_week)].append(s.id)

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
    # --------------------------------------------------------
    rest_delta = timedelta(hours=REST_HOURS)

    for d_id in doctor_ids:
        for i, s1 in enumerate(shifts):
            for j, s2 in enumerate(shifts):
                if j <= i:
                    continue

                overlap = shifts_overlap(s1.start, s1.end, s2.start, s2.end)

                rest_violation_forward = (
                    s2.start < s1.end + rest_delta and s2.start >= s1.start
                )
                rest_violation_backward = (
                    s1.start < s2.end + rest_delta and s1.start >= s2.start
                )

                if overlap or rest_violation_forward or rest_violation_backward:
                    model += (
                        x[(d_id, s1.id)] + x[(d_id, s2.id)] <= 1,
                        f"NoOverlapOrRest_{d_id}_{s1.id}_{s2.id}",
                    )

    # --------------------------------------------------------
    # 4) PER-DOCTOR MIN & MAX SHIFTS (MONTH)
    # --------------------------------------------------------
    total_shifts_expr = {}
    for d in doctors:
        total_shifts_for_d = pulp.lpSum(x[(d.id, s.id)] for s in shifts)
        total_shifts_expr[d.id] = total_shifts_for_d

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
    leave_rows = get_all_leave()
    leave_map: dict[str, list[tuple[str, str]]] = {}
    for row in leave_rows:
        doc_id = row["doctor_external_id"]
        if doc_id not in doctor_by_id:
            continue
        leave_map.setdefault(doc_id, []).append(
            (row["start_date"], row["end_date"])
        )

    for d_id, intervals in leave_map.items():
        for s in shifts:
            shift_date_str = s.start.date().isoformat()
            for (start_str, end_str) in intervals:
                if start_str <= shift_date_str <= end_str:
                    model += (
                        x[(d_id, s.id)] == 0,
                        f"Leave_{d_id}_{s.id}_{start_str}_{end_str}",
                    )
                    break

    # --------------------------------------------------------
    # 6) WEEKEND LOAD: 1–3 WEEKENDS PER DOCTOR
    #    Weekend = any Sat/Sun shift; 2 is "ideal" (enforced later via fairness)
    # --------------------------------------------------------
    weekend_var: dict[tuple[str, tuple[int, int]], pulp.LpVariable] = {}

    for d_id in doctor_ids:
        for w_key, shift_list in weekends.items():
            if not shift_list:
                continue
            var = pulp.LpVariable(
                f"wk_{d_id}_{w_key[0]}_{w_key[1]}",
                cat=pulp.LpBinary,
            )
            weekend_var[(d_id, w_key)] = var

            # If weekend_var = 1 => at least one shift that weekend
            model += (
                pulp.lpSum(x[(d_id, sid)] for sid in shift_list) >= var,
                f"WeekendLower_{d_id}_{w_key}",
            )
            # If no shifts => weekend_var must be 0
            model += (
                pulp.lpSum(x[(d_id, sid)] for sid in shift_list)
                <= len(shift_list) * var,
                f"WeekendUpper_{d_id}_{w_key}",
            )

    all_weekend_keys = list(weekends.keys())

    if all_weekend_keys:
        for d_id in doctor_ids:
            # Sum of weekends this doctor works
            wk_sum = pulp.lpSum(
                weekend_var.get((d_id, w_key), 0)
                for w_key in all_weekend_keys
            )
            # Hard bounds: at least 1, at most 3
            model += (
                wk_sum >= 1,
                f"Min1Weekend_{d_id}",
            )
            model += (
                wk_sum <= 3,
                f"Max3Weekends_{d_id}",
            )

    # --------------------------------------------------------
    # 7) FRIDAY–SATURDAY–SUNDAY NIGHT BLOCKS (for nights only)
    # --------------------------------------------------------
    # If doctor works Friday night => must also work Sat & Sun night of same weekend
    for (iso_year, iso_week), nights_dict in weekend_nights.items():
        fri_id = nights_dict.get("fri")
        sat_id = nights_dict.get("sat")
        sun_id = nights_dict.get("sun")

        if fri_id is None or sat_id is None or sun_id is None:
            continue  # skip incomplete weekend nights

        for d_id in doctor_ids:
            # If they do Fri night, they must also be on Sat & Sun night
            model += (
                x[(d_id, fri_id)] <= x[(d_id, sat_id)],
                f"FriImpliesSat_{d_id}_{iso_year}_{iso_week}",
            )
            model += (
                x[(d_id, fri_id)] <= x[(d_id, sun_id)],
                f"FriImpliesSun_{d_id}_{iso_year}_{iso_week}",
            )

    # --------------------------------------------------------
    # 8) MAX 2 WEEKDAY NIGHTS (MON–THU) PER WEEK
    # --------------------------------------------------------
    for (iso_year, iso_week), night_ids in weekday_nights_per_week.items():
        if not night_ids:
            continue
        for d_id in doctor_ids:
            model += (
                pulp.lpSum(x[(d_id, sid)] for sid in night_ids)
                <= 2,
                f"Max2WeeknightNights_{d_id}_{iso_year}_{iso_week}",
            )

    # --------------------------------------------------------
    # 9) MAX 3 CONSECUTIVE NIGHTS
    # --------------------------------------------------------
    dates_sorted = sorted(night_shift_by_date.keys())

    for i in range(len(dates_sorted) - 3):
        d0 = dates_sorted[i]
        d1 = dates_sorted[i + 1]
        d2 = dates_sorted[i + 2]
        d3 = dates_sorted[i + 3]

        if (d1 - d0).days == 1 and (d2 - d1).days == 1 and (d3 - d2).days == 1:
            s0 = night_shift_by_date[d0]
            s1 = night_shift_by_date[d1]
            s2 = night_shift_by_date[d2]
            s3 = night_shift_by_date[d3]

            for d_id in doctor_ids:
                model += (
                    x[(d_id, s0)]
                    + x[(d_id, s1)]
                    + x[(d_id, s2)]
                    + x[(d_id, s3)]
                    <= 3,
                    f"Max3ConsecNights_{d_id}_{d0}",
                )

    # --------------------------------------------------------
    # OBJECTIVE: FAIRNESS IN TOTAL SHIFTS + NIGHT SHIFTS
    # --------------------------------------------------------
    # Total shifts (existing)
    max_shifts_var = pulp.LpVariable("max_shifts_per_doctor", lowBound=0)
    min_shifts_var = pulp.LpVariable("min_shifts_per_doctor", lowBound=0)

    for d in doctors:
        model += total_shifts_expr[d.id] <= max_shifts_var
        model += total_shifts_expr[d.id] >= min_shifts_var

    spread_total = max_shifts_var - min_shifts_var

    # Night shift fairness
    night_shifts_expr = {}
    if night_shift_ids:
        max_nights_var = pulp.LpVariable("max_nights_per_doctor", lowBound=0)
        min_nights_var = pulp.LpVariable("min_nights_per_doctor", lowBound=0)

        for d in doctors:
            night_count = pulp.lpSum(
                x[(d.id, sid)] for sid in night_shift_ids
            )
            night_shifts_expr[d.id] = night_count
            model += night_count <= max_nights_var
            model += night_count >= min_nights_var

        spread_nights = max_nights_var - min_nights_var
    else:
        # No night shifts in this schedule
        spread_nights = 0

    # Combined objective:
    #   weight_total * spread_total  +  weight_nights * spread_nights
    # Tune weights if needed
    weight_total = 1.0
    weight_nights = 1.0

    model += weight_total * spread_total + weight_nights * spread_nights

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


