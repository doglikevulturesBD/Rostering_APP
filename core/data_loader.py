# core/data_loader.py
import pandas as pd
from datetime import datetime
from typing import List
from .models import Doctor, Shift

def load_doctors_from_csv(path: str) -> List[Doctor]:
    df = pd.read_csv(path)
    doctors = []
    for _, row in df.iterrows():
        doctors.append(
            Doctor(
                id=str(row["id"]),
                name=row["name"],
                level=row.get("level", "MO"),
                firm=row.get("firm", None),
                contract_hours_per_month=row.get("contract_hours", 175),
                min_shifts_per_month=row.get("min_shifts", 16),
                max_shifts_per_month=row.get("max_shifts", 18),
            )
        )
    return doctors

def load_shifts_from_csv(path: str) -> List[Shift]:
    df = pd.read_csv(path)
    shifts = []
    for _, row in df.iterrows():
        start = datetime.fromisoformat(row["start"])
        end = datetime.fromisoformat(row["end"])
        shifts.append(
            Shift(
                id=str(row["id"]),
                name=row["name"],
                start=start,
                end=end,
                is_weekend=bool(row["is_weekend"]),
                is_night=bool(row["is_night"]),
                intensity=int(row.get("intensity", 3)),
                min_doctors=int(row.get("min_doctors", 1)),
                max_doctors=int(row.get("max_doctors", 2)),
            )
        )
    return shifts

