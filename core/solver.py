# core/solver.py

from typing import List
from .models import Doctor, Shift, Assignment, Roster


def generate_naive_roster(doctors: List[Doctor], shifts: List[Shift]) -> Roster:
    """
    Very simple allocator:
    - Loops through all shifts
    - For each shift, assigns `min_doctors` doctors round-robin
    - No rules, no fairness, just coverage test

    This is just for testing the full pipeline. We'll replace it later with OR-Tools.
    """
    assignments: List[Assignment] = []
    doc_index = 0
    num_docs = len(doctors)

    if num_docs == 0:
        return Roster(doctors=doctors, shifts=shifts, assignments=[])

    for shift in shifts:
        for _ in range(shift.min_doctors):
            doctor = doctors[doc_index % num_docs]
            assignments.append(
                Assignment(
                    doctor_id=doctor.id,
                    shift_id=shift.id,
                )
            )
            doc_index += 1

    return Roster(doctors=doctors, shifts=shifts, assignments=assignments)
