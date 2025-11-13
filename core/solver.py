from typing import List
from .models import Doctor, Shift, Assignment, Roster

def generate_naive_roster(doctors: List[Doctor], shifts: List[Shift]) -> Roster:
    assignments = []
    doc_index = 0
    n = len(doctors)

    for shift in shifts:
        for _ in range(shift.min_doctors):  # assign minimum coverage
            doctor = doctors[doc_index % n]
            assignments.append(
                Assignment(doctor_id=doctor.id, shift_id=shift.id)
            )
            doc_index += 1

    return Roster(doctors=doctors, shifts=shifts, assignments=assignments)
