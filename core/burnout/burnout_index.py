# core/burnout/burnout_index.py
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Tuple

from ..models import Doctor, Shift, Assignment

def _build_lookup(shifts: List[Shift]) -> Dict[str, Shift]:
    return {s.id: s for s in shifts}

def compute_doctor_hours(assignments: List[Assignment],
                         shifts: List[Shift]) -> Dict[str, float]:
    shift_lookup = _build_lookup(shifts)
    hours_per_doctor: Dict[str, float] = defaultdict(float)
    for a in assignments:
        shift = shift_lookup[a.shift_id]
        hours_per_doctor[a.doctor_id] += shift.duration_hours
    return hours_per_doctor

def _get_shift_history_for_doctor(doctor_id: str,
                                  assignments: List[Assignment],
                                  shifts: List[Shift]
                                  ) -> List[Shift]:
    shift_lookup = _build_lookup(shifts)
    return [
        shift_lookup[a.shift_id]
        for a in assignments
        if a.doctor_id == doctor_id
    ]

def _max_consecutive_days(shift_history: List[Shift]) -> int:
    if not shift_history:
        return 0
    days = sorted({s.start.date() for s in shift_history})
    max_streak = 1
    current_streak = 1
    for prev, curr in zip(days, days[1:]):
        if (curr - prev).days == 1:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 1
    return max_streak

def _count_nights(shift_history: List[Shift], window_days: int = 7,
                  ref: datetime | None = None) -> int:
    if ref is None:
        ref = max(s.start for s in shift_history) if shift_history else datetime.now()
    start_window = ref.date().toordinal() - window_days
    return sum(
        1 for s in shift_history
        if s.is_night and s.start.toordinal() >= start_window
    )

def compute_burnout_scores(doctors: List[Doctor],
                           shifts: List[Shift],
                           assignments: List[Assignment]
                           ) -> Dict[str, Dict]:
    """
    Returns dict:
    { doctor_id: {
        "score": float (0-10),
        "label": "low"/"medium"/"high",
        "details": {...}
      }
    }
    """
    scores: Dict[str, Dict] = {}
    shift_lookup = _build_lookup(shifts)

    # group assignments by doctor
    assignments_by_doc: Dict[str, List[Assignment]] = defaultdict(list)
    for a in assignments:
        assignments_by_doc[a.doctor_id].append(a)

    for doc in doctors:
        hist = _get_shift_history_for_doctor(doc.id, assignments, shifts)

        # hours and nights
        total_hours = sum(s.duration_hours for s in hist)
        nights_7d = _count_nights(hist, window_days=7)
        nights_30d = _count_nights(hist, window_days=30)
        max_streak = _max_consecutive_days(hist)
        weekend_shifts = sum(1 for s in hist if s.is_weekend)

        # simple scoring model (you can tweak weights later)
        score = 0.0

        # total hours
        if total_hours > 180:
            score += 2
        if total_hours > 200:
            score += 1

        # recent nights
        if nights_7d >= 3:
            score += 2
        if nights_7d >= 4:
            score += 1

        # month nights
        if nights_30d >= 6:
            score += 1

        # consecutive days
        if max_streak >= 5:
            score += 2
        if max_streak >= 7:
            score += 1

        # weekend load
        if weekend_shifts >= 4:
            score += 1

        # clamp 0–10
        score = max(0.0, min(10.0, score))

        if score <= 3:
            label = "low"
        elif score <= 6:
            label = "medium"
        else:
            label = "high"

        scores[doc.id] = {
            "score": score,
            "label": label,
            "details": {
                "total_hours": total_hours,
                "nights_7d": nights_7d,
                "nights_30d": nights_30d,
                "max_consecutive_days": max_streak,
                "weekend_shifts": weekend_shifts,
            },
        }

    return scores

