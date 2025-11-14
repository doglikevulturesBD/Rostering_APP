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
    """
    Build pairs of shifts that a single doctor cannot work together
    due to overlap or insufficient rest.
    """
    conflict_pairs: List[Tuple[int, int]] = []
    n = len(shifts)

    for i in range(n):
        for j in range(i + 1, n):
            s1 = shifts[i]
            s2 = shifts[j]

            overlapping = not (s1.end <= s2.start or s2.end <= s1.start)
            insufficient_rest = False

            # rest from s1 -> s2
            if s1.end <= s2.start:
                rest_12 = _hours_between(s1.end, s2.start)
                if rest_12 < rest_hours_required:
                    insufficient_rest = True

            # rest from s2 -> s1
            if s2.end <= s1.start:
                rest_21 = _hours_between(s2.end, s1.start)
                if rest_21 < rest_hours_required:
                    insufficient_rest = True

            if overlapping or insufficient_rest:
                conflict_pairs.append((i, j))

    return conflict_pairs


def _find_weekend_night_bundles(shifts: List[Shift]) -> List[Tuple[int, int, int]]:
    """
    Identify (Fri night, Sat night, Sun night) triplets that should
    be assigned as a bundle for each doctor (0 or 3 nights).
    """
    # map (date -> shift_idx) for night shifts
    night_by_date: Dict[date, int] = {}
    for idx, s in enumerate(shifts):
        # consider night shift if starts after 21:00
        if s.start.hour >= 21:
            night_by_date[s.start.date()] = idx

    bundles: List[Tuple[int, int, int]] = []

    # look for Fridays that have corresponding Sat & Sun nights
    for d in sorted(night_by_date.keys()):
        if d.weekday() == 4:  # Friday
            fri = d
            sat = date.fromordinal(fri.toordinal() + 1)
            sun = date.fromordinal(fri.toordinal() + 2)
            if sat in night_by_date and sun in night_by_date:
                fri_idx = night_by_date[fri]
                sat_idx = night_by_date[sat]
                sun_idx = night_by_date[sun]
                bundles.append((fri_idx, sat_idx, sun_idx))

    return bundles


def generate_optimized_roster(
    doctors: List[Doctor],
    shifts: List[Shift],
    leave_rows=None,
    rest_hours_required: float = 11.0,
) -> Roster:
    """
    Optimised roster using PuLP with:
      - hard constraints:
          * shift staffing (min/max doctors)
          * doctor min/max number of shifts
          * rest rules and overlap
          * leave
          * weekend night bundle: Fri+Sat+Sun nights as 0 or 3
      - soft constraints (penalty-based objective):
          * deviation from contract hours
          * night shift fairness
          * weekend shift fairness
    """
    if not doctors or not shifts:
        return Roster(doctors=doctors, shifts=shifts, assignments=[])

    num_doctors = len(doctors)
    num_shifts = len(shifts)

    leave_map = _build_leave_map(leave_rows or [])
    conflict_pairs = _build_conflict_pairs(shifts, rest_hours_required)
    weekend_night_bundles = _find_weekend_night_bundles(shifts)

    model = pulp.LpProblem("ED_Roster_Optimisation", pulp.LpMinimize)

    # Decision vars: x[d,s] ∈ {0,1}
    x: Dict[Tuple[int, int], pulp.LpVariable] = {}
    for d_idx in range(num_doctors):
        for s_idx in range(num_shifts):
            x[(d_idx, s_idx)] = pulp.LpVariable(
                f"x_{doctors[d_idx].id}_{shifts[s_idx].id}",
                lowBound=0,
                upBound=1,
                cat=pulp.LpBinary,
            )

    # Precompute night and weekend indices
    night_indices = [
        i for i, s in enumerate(shifts) if s.start.hour >= 21
    ]
    weekend_indices = [
        i for i, s in enumerate(shifts) if s.is_weekend
    ]

    total_night_slots = sum(
        shifts[i].min_doctors for i in night_indices
    ) if night_indices else 0
    total_weekend_slots = sum(
        shifts[i].min_doctors for i in weekend_indices
    ) if weekend_indices else 0

    target_nights = total_night_slots / num_doctors if num_doctors > 0 else 0.0
    target_weekends = total_weekend_slots / num_doctors if num_doctors > 0 else 0.0

    # ----------------------------------------------------
    # HARD CONSTRAINTS
    # ----------------------------------------------------

    # 1. Shift staffing (min/max)
    for s_idx, sh in enumerate(shifts):
        assigned = [x[(d_idx, s_idx)] for d_idx in range(num_doctors)]
        if sh.min_doctors is not None:
            model += pulp.lpSum(assigned) >= sh.min_doctors, f"shift_{sh.id}_min"
        if sh.max_doctors is not None:
            model += pulp.lpSum(assigned) <= sh.max_doctors, f"shift_{sh.id}_max"

    # 2. Doctor min/max number of shifts
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

    # 3. Conflicts (overlap + rest)
    for d_idx, doc in enumerate(doctors):
        for (i, j) in conflict_pairs:
            model += x[(d_idx, i)] + x[(d_idx, j)] <= 1, f"conflict_{doc.id}_{i}_{j}"

    # 4. Leave: no shifts during leave periods
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

    # 5. Weekend night bundle (Fri, Sat, Sun nights must be all 0 or all 1)
    for d_idx, doc in enumerate(doctors):
        for (fri_idx, sat_idx, sun_idx) in weekend_night_bundles:
            # enforce equality: x_fri == x_sat == x_sun
            model += x[(d_idx, fri_idx)] - x[(d_idx, sat_idx)] == 0, f"bundle1_{doc.id}_{fri_idx}"
            model += x[(d_idx, sat_idx)] - x[(d_idx, sun_idx)] == 0, f"bundle2_{doc.id}_{fri_idx}"

    # ----------------------------------------------------
    # SOFT CONSTRAINTS (Penalty Objective)
    # ----------------------------------------------------

    # Weights (tune later if needed)
    W_HOURS_DEV = 0.05
    W_NIGHT_FAIR = 2.0
    W_WEEKEND_FAIR = 1.5

    penalty_terms = []

    for d_idx, doc in enumerate(doctors):
        # hours: h_d
        h_d = pulp.lpSum(
            x[(d_idx, s_idx)] * shifts[s_idx].duration_hours
            for s_idx in range(num_shifts)
        )

        # deviation from contract hours
        dev_h_pos = pulp.LpVariable(f"dev_h_pos_{doc.id}", lowBound=0)
        dev_h_neg = pulp.LpVariable(f"dev_h_neg_{doc.id}", lowBound=0)
        model += (
            h_d - doc.contract_hours_per_month
            == dev_h_pos - dev_h_neg,
            f"hours_dev_{doc.id}",
        )
        penalty_terms.append(W_HOURS_DEV * (dev_h_pos + dev_h_neg))

        # night fairness
        if night_indices:
            n_d = pulp.lpSum(
                x[(d_idx, s_idx)] for s_idx in night_indices
            )
            dev_n_pos = pulp.LpVariable(f"dev_n_pos_{doc.id}", lowBound=0)
            dev_n_neg = pulp.LpVariable(f"dev_n_neg_{doc.id}", lowBound=0)
            model += (
                n_d - target_nights
                == dev_n_pos - dev_n_neg,
                f"night_dev_{doc.id}",
            )
            penalty_terms.append(W_NIGHT_FAIR * (dev_n_pos + dev_n_neg))

        # weekend fairness
        if weekend_indices:
            w_d = pulp.lpSum(
                x[(d_idx, s_idx)] for s_idx in weekend_indices
            )
            dev_w_pos = pulp.LpVariable(f"dev_w_pos_{doc.id}", lowBound=0)
            dev_w_neg = pulp.LpVariable(f"dev_w_neg_{doc.id}", lowBound=0)
            model += (
                w_d - target_weekends
                == dev_w_pos - dev_w_neg,
                f"weekend_dev_{doc.id}",
            )
            penalty_terms.append(W_WEEKEND_FAIR * (dev_w_pos + dev_w_neg))

    # Objective: minimize sum of penalties
    if penalty_terms:
        model += pulp.lpSum(penalty_terms), "TotalPenalty"
    else:
        # fallback if no soft terms
        model += 0, "DummyObjective"

    # Solve
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
