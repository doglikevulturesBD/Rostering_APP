# core/solver.py

from typing import List
from core.models import Doctor, Shift, Assignment, Roster


def generate_naive_roster(doctors: List[Doctor], shifts: List[Shift]) -> Roster:
    assignments = []
    doc_index = 0
    num_docs = len(doctors)

    if num_docs == 0:
        return Roster(doctors, shifts, [])

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

    return Roster(doctors, shifts, assignments)
