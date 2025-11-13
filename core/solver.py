# core/solver.py
from typing import List
from .models import Doctor, Shift, Assignment, Roster

def generate_naive_roster(doctors: List[Doctor],
                          shifts: List[Shift]) -> Roster:
    """
    Very simple round-robin allocator.
    Replace this later with OR-Tools CP-SAT model.
    """
    assignments: List[Assignment] = []
    doc_index = 0
    num_docs = len(doctors)

    for shift in shifts:
        required = shift.min_doctors
        for _ in range(required):
            doctor = doctors[doc_index % num_docs]
            assignments.append(Assignment(doctor_id=doctor.id, shift_id=shift.id))
            doc_index += 1

    return Roster(doctors=doctors, shifts=shifts, assignments=assignments)

