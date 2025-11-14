# core/database.py

import os
import sqlite3
from datetime import datetime
from typing import List, Optional

from core.models import Doctor, Shift

DB_PATH = os.path.join("data", "roster.db")


def get_connection():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Doctors table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS doctors (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            level TEXT NOT NULL,
            firm INTEGER,
            contract_hours INTEGER NOT NULL,
            min_shifts INTEGER NOT NULL,
            max_shifts INTEGER NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        )
        """
    )

    # Shifts table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            duration_hours REAL NOT NULL,
            min_doctors INTEGER NOT NULL,
            max_doctors INTEGER NOT NULL,
            is_weekend INTEGER NOT NULL
        )
        """
    )

    # Leave requests table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS leave_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_external_id TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            leave_type TEXT NOT NULL,
            reason TEXT,
            FOREIGN KEY (doctor_external_id) REFERENCES doctors(id)
        )
        """
    )

    conn.commit()
    conn.close()


# -------------------------------------------------------
# DOCTORS
# -------------------------------------------------------

def _generate_doctor_id(name: str) -> str:
    # Simple deterministic ID from name + timestamp
    return f"DOC_{name[:3].upper()}_{int(datetime.now().timestamp())}"


def create_doctor(
    name: str,
    level: str,
    firm: Optional[int],
    contract_hours: int,
    min_shifts: int,
    max_shifts: int,
) -> Doctor:
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    doc_id = _generate_doctor_id(name)

    cur.execute(
        """
        INSERT INTO doctors (id, name, level, firm, contract_hours, min_shifts, max_shifts, active)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (doc_id, name, level, firm, contract_hours, min_shifts, max_shifts),
    )
    conn.commit()
    conn.close()

    return Doctor(
        id=doc_id,
        name=name,
        level=level,
        firm=firm,
        contract_hours_per_month=contract_hours,
        min_shifts_per_month=min_shifts,
        max_shifts_per_month=max_shifts,
        active=True,
    )


def get_all_doctors(active_only: bool = True) -> List[Doctor]:
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    if active_only:
        cur.execute("SELECT * FROM doctors WHERE active = 1 ORDER BY name")
    else:
        cur.execute("SELECT * FROM doctors ORDER BY name")

    rows = cur.fetchall()
    conn.close()

    docs: List[Doctor] = []
    for r in rows:
        docs.append(
            Doctor(
                id=r["id"],
                name=r["name"],
                level=r["level"],
                firm=r["firm"],
                contract_hours_per_month=r["contract_hours"],
                min_shifts_per_month=r["min_shifts"],
                max_shifts_per_month=r["max_shifts"],
                active=bool(r["active"]),
            )
        )
    return docs


def update_doctor_hours_and_shifts(
    external_id: str,
    contract_hours: int,
    min_shifts: int,
    max_shifts: int,
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE doctors
        SET contract_hours = ?, min_shifts = ?, max_shifts = ?
        WHERE id = ?
        """,
        (contract_hours, min_shifts, max_shifts, external_id),
    )
    conn.commit()
    conn.close()


def deactivate_doctor(external_id: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE doctors SET active = 0 WHERE id = ?",
        (external_id,),
    )
    conn.commit()
    conn.close()


# -------------------------------------------------------
# SHIFTS
# -------------------------------------------------------

def save_generated_shifts(shift_rows):
    """
    shift_rows: list of dicts with keys:
        date, start_time, end_time, duration_hours,
        min_doctors, max_doctors, is_weekend
    """
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    # wipe existing shifts for now (one month at a time)
    cur.execute("DELETE FROM shifts")

    for s in shift_rows:
        cur.execute(
            """
            INSERT INTO shifts (
                date,
                start_time,
                end_time,
                duration_hours,
                min_doctors,
                max_doctors,
                is_weekend
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                s["date"],
                s["start_time"],
                s["end_time"],
                s["duration_hours"],
                s["min_doctors"],
                s["max_doctors"],
                s["is_weekend"],
            ),
        )

    conn.commit()
    conn.close()


def load_shifts() -> List[Shift]:
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM shifts ORDER BY date, start_time")
    rows = cur.fetchall()
    conn.close()

    shifts: List[Shift] = []
    for r in rows:
        start_dt = datetime.fromisoformat(r["start_time"])
        end_dt = datetime.fromisoformat(r["end_time"])
        shifts.append(
            Shift(
                id=r["id"],
                start=start_dt,
                end=end_dt,
                duration_hours=r["duration_hours"],
                min_doctors=r["min_doctors"],
                max_doctors=r["max_doctors"],
                is_weekend=bool(r["is_weekend"]),
            )
        )
    return shifts


# -------------------------------------------------------
# LEAVE
# -------------------------------------------------------

def create_leave(
    doctor_external_id: str,
    start_date: datetime,
    end_date: datetime,
    leave_type: str,
    reason: str = "",
):
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO leave_requests
        (doctor_external_id, start_date, end_date, leave_type, reason)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            doctor_external_id,
            start_date.date().isoformat(),
            end_date.date().isoformat(),
            leave_type,
            reason,
        ),
    )
    conn.commit()
    conn.close()


def get_all_leave():
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM leave_requests ORDER BY start_date")
    rows = cur.fetchall()
    conn.close()
    return rows


def delete_leave(leave_id: int):
    init_db()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM leave_requests WHERE id = ?", (leave_id,))
    conn.commit()
    conn.close()

# -------------------------------
#   LOAD SHIFTS FROM DATABASE
# -------------------------------
def load_shifts():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT external_id, date, start_time, end_time, is_weekend
        FROM shifts
        ORDER BY date, start_time
    """)

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "external_id": r[0],
            "date": r[1],
            "start_time": r[2],
            "end_time": r[3],
            "is_weekend": r[4]
        }
        for r in rows
    ]


# -------------------------------
#   LOAD ASSIGNMENTS (Doctor → Shift)
# -------------------------------
def load_assignments():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT doctor_external_id, shift_external_id
        FROM assignments
        ORDER BY shift_external_id
    """)

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "doctor": r[0],
            "shift": r[1]
        }
        for r in rows
    ]


# -------------------------------
#   GET ALL DOCTORS (safe version)
# -------------------------------
def get_all_doctors(active_only=True):
    conn = get_connection()
    cur = conn.cursor()

    if active_only:
        cur.execute("""
            SELECT external_id, name, level, firm,
                   contract_hours_per_month, 
                   min_shifts_per_month, 
                   max_shifts_per_month
            FROM doctors
            WHERE active = 1
            ORDER BY name
        """)
    else:
        cur.execute("""
            SELECT external_id, name, level, firm,
                   contract_hours_per_month, 
                   min_shifts_per_month, 
                   max_shifts_per_month
            FROM doctors
            ORDER BY name
        """)

    rows = cur.fetchall()
    conn.close()

    return [
        {
            "external_id": r[0],
            "name": r[1],
            "level": r[2],
            "firm": r[3],
            "contract_hours": r[4],
            "min_shifts": r[5],
            "max_shifts": r[6]
        }
        for r in rows
    ]

