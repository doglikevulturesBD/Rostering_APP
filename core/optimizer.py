# core/optimizer.py

import itertools
from datetime import datetime, timedelta
import pulp
from core.models import AssignmentResult, Assignment

# -------------------------------------------------------
# Helper functions
# -------------------------------------------------------

def is_night_shift(shift):
    """Night shift = start at or after 21:00."""
    return shift.start.hour >= 21


def is_weeknight(shift):
    """True if night AND Monday–Thursday."""
    return is_night_shift(shift) and shift.start.weekday() < 4


def is_weekend(shift):
    return shift.start.weekday() >= 5


def same_day(s1, s2):
    return s1.start.date() == s2.start.date()


def shift_gap_hours(s1, s2):
    """Positive hours between shifts if s2 follows s1."""
    return (s2.start - s1.end).total_seconds() / 3600.0


# -------------------------------------------------------
# Main Optimizer
# -------------------------------------------------------

def build_and_solve_roster(shifts, doctors):
    """
    shifts  = list[Shift]
    doctors = list[Doctor]
    """

    model = pulp.LpProblem("Doctor_Rostering", pulp.LpMinimize)

    # DECISION VARIABLES
    X = pulp.LpVariable.dicts(
        "assign",
        ((d.id, s.id) for d in doctors for s in shifts),
        lowBound=0,
        upBound=1,
        cat="Binary",
    )

    # ---------------------------------------------------
    # 1. COVERAGE CONSTRAINTS
    # ---------------------------------------------------
    for s in shifts:
        model += (
            pulp.lpSum(X[(d.id, s.id)] for d in doctors)
            >= s.min_doctors,
            f"min_coverage_s{s.id}",
        )
        model += (
            pulp.lpSum(X[(d.id, s.id)] for d in doctors)
            <= s.max_doctors,
            f"max_coverage_s{s.id}",
        )

    # ---------------------------------------------------
    # 2. DOCTOR CANNOT WORK TWO SHIFTS IN ONE DAY
    # ---------------------------------------------------
    for d in doctors:
        for day, group in itertools.groupby(
            sorted(shifts, key=lambda s: s.start.date()),
            key=lambda s: s.start.date(),
        ):
            group = list(group)
            model += (
                pulp.lpSum(X[(d.id, s.id)] for s in group) <= 1,
                f"one_shift_per_day_{d.id}_{day}",
            )

    # ---------------------------------------------------
    # 3. REST PERIOD ≥ 11 HOURS
    # ---------------------------------------------------
    for d in doctors:
        for s1, s2 in itertools.permutations(shifts, 2):
            if s2.start > s1.start:
                gap = shift_gap_hours(s1, s2)
                if gap < 11:
                    model += (
                        X[(d.id, s1.id)] + X[(d.id, s2.id)] <= 1,
                        f"rest_gap_{d.id}_{s1.id}_{s2.id}",
                    )

    # ---------------------------------------------------
    # 4. NO MORE THAN 3 CONSECUTIVE NIGHT SHIFTS
    # ---------------------------------------------------
    night_shifts = [s for s in shifts if is_night_shift(s)]
    night_shifts_sorted = sorted(night_shifts, key=lambda s: s.start)

    for d in doctors:
        for i in range(len(night_shifts_sorted) - 3):
            block = night_shifts_sorted[i : i + 4]
            model += (
                pulp.lpSum(X[(d.id, s.id)] for s in block) <= 3,
                f"max_3_nights_row_{d.id}_{i}",
            )

    # ---------------------------------------------------
    # 5. WEEKLY LIMIT: MAX 2 WEEKNIGHT NIGHT SHIFTS
    # ---------------------------------------------------
    for d in doctors:
        for week in range(1, 6):  # week 1–5
            week_nights = [
                s for s in night_shifts
                if is_weeknight(s) and s.start.isocalendar().week == week
            ]
            if week_nights:
                model += (
                    pulp.lpSum(X[(d.id, s.id)] for s in week_nights) <= 2,
                    f"max_weeknight_{d.id}_week{week}",
                )

    # ---------------------------------------------------
    # 6. FRI–SAT–SUN NIGHT BLOCK RULE
    # ---------------------------------------------------
    friday_nights = [s for s in night_shifts if s.start.weekday() == 4]
    saturday_nights = [s for s in night_shifts if s.start.weekday() == 5]
    sunday_nights = [s for s in night_shifts if s.start.weekday() == 6]

    for d in doctors:
        for f in friday_nights:
            for s in saturday_nights:
                if s.start.date() == f.start.date() + timedelta(days=1):
                    model += (
                        X[(d.id, f.id)] <= X[(d.id, s.id)],
                        f"fri_sat_block_{d.id}_{f.id}",
                    )
            for su in sunday_nights:
                if su.start.date() == f.start.date() + timedelta(days=2):
                    model += (
                        X[(d.id, f.id)] <= X[(d.id, su.id)],
                        f"fri_sun_block_{d.id}_{f.id}",
                    )

    # ---------------------------------------------------
    # SOFT CONSTRAINTS (OBJECTIVE)
    # ---------------------------------------------------
    night_penalties = []
    fairness_penalties = []
    overload_penalties = []

    for d in doctors:
        num_nights = pulp.lpSum(
            X[(d.id, s.id)] for s in shifts if is_night_shift(s)
        )

        # Prefer 2–4 nights, allow 5 but penalize above
        night_penalties.append(0.5 * pulp.lpSum((num_nights - 3) ** 2))

        # Total shifts fairness
        total_shifts = pulp.lpSum(X[(d.id, s.id)] for s in shifts)
        fairness_penalties.append(0.2 * (total_shifts - (len(shifts) / len(doctors))) ** 2)

        # Prevent night overload
        overload_penalties.append(1.5 * pulp.lpSum(pulp.max_(0, num_nights - 5)))

    model += (
        pulp.lpSum(night_penalties)
        + pulp.lpSum(fairness_penalties)
        + pulp.lpSum(overload_penalties)
    )

    # ---------------------------------------------------
    # SOLVE
    # ---------------------------------------------------
    result = model.solve(pulp.PULP_CBC_CMD(msg=False))

    if result != pulp.LpStatusOptimal:
        raise ValueError("❌ No feasible solution found")

    # ---------------------------------------------------
    # BUILD RESULT
    # ---------------------------------------------------
    assignments = []
    for d in doctors:
        for s in shifts:
            if pulp.value(X[(d.id, s.id)]) == 1:
                assignments.append(Assignment(doctor_id=d.id, shift_id=s.id))

    return AssignmentResult(assignments=assignments)



