# core/analytics.py
from typing import List, Dict
from collections import defaultdict
from .models import Doctor, Shift, Assignment

def compute_doctor_hours_summary(doctors: List[Doctor],
                                 shifts: List[Shift],
                                 assignments: List[Assignment]) -> List[Dict]:
    shift_lookup = {s.id: s for s in shifts}
    hours = defaultdict(float)
    num_shifts = defaultdict(int)
    nights = defaultdict(int)
    weekends = defaultdict(int)

    for a in assignments:
        s = shift_lookup[a.shift_id]
        hours[a.doctor_id] += s.duration_hours
        num_shifts[a.doctor_id] += 1
        if s.is_night:
            nights[a.doctor_id] += 1
        if s.is_weekend:
            weekends[a.doctor_id] += 1

    out = []
    for d in doctors:
        out.append({
            "doctor_id": d.id,
            "name": d.name,
            "level": d.level,
            "total_hours": hours[d.id],
            "num_shifts": num_shifts[d.id],
            "night_shifts": nights[d.id],
            "weekend_shifts": weekends[d.id],
            "contract_hours": d.contract_hours_per_month,
        })
    return out

