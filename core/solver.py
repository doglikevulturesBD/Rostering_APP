# core/solver.py

from typing import List, Dict

from core.models import Doctor, Shift, Assignment, Roster


def generate_naive_roster(
    doctors: List[Doctor],
    shifts: List[Shift],
) -> Roster:
    """
    Simple round-robin assignment:
    - ignores rest rules and leave
    - respects max_shifts_per_month and min_doctors per shift
    """

    assignments: List[Assignment] = []
    if not doctors or not shifts:
        return Roster(doctors=doctors, shifts=shifts, assignments=assignments)

    # track how many shifts each doctor has
    shift_count: Dict[str, int] = {d.id: 0 for d in doctors}
    doc_index = 0
    num_docs = len(doctors)

    for sh in shifts:
        needed = sh.min_doctors or 1
        assigned_here = 0
        # simple loop to assign needed doctors
        attempts = 0
        while assigned_here < needed and attempts < num_docs * 2:
            doc = doctors[doc_index]
            doc_index = (doc_index + 1) % num_docs
            attempts += 1

            max_shifts = doc.max_shifts_per_month or 999
            if shift_count[doc.id] >= max_shifts:
                continue

            assignments.append(Assignment(doctor_id=doc.id, shift_id=sh.id))
            shift_count[doc.id] += 1
            assigned_here += 1

    return Roster(doctors=doctors, shifts=shifts, assignments=assignments)
