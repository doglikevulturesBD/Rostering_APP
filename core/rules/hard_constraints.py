# core/rules/hard_constraints.py
from datetime import timedelta
from typing import List, Dict
from ..models import Doctor, Shift, Assignment

MIN_REST_HOURS = 18

def check_min_rest(assignments: List[Assignment],
                   shifts: List[Shift]) -> Dict[str, int]:
    """
    Returns doctor_id -> number of rest violations.
    """
    shift_lookup = {s.id: s for s in shifts}
    # group by doc
    by_doc: Dict[str, List[Shift]] = {}
    for a in assignments:
        by_doc.setdefault(a.doctor_id, []).append(shift_lookup[a.shift_id])

    violations: Dict[str, int] = {}
    for doc_id, hist in by_doc.items():
        hist_sorted = sorted(hist, key=lambda s: s.start)
        v = 0
        for prev, curr in zip(hist_sorted, hist_sorted[1:]):
            rest_hours = (curr.start - prev.end).total_seconds() / 3600.0
            if rest_hours < MIN_REST_HOURS:
                v += 1
        violations[doc_id] = v
    return violations

