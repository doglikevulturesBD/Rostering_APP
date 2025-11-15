# core/database.py

import os
import sqlite3
from datetime import datetime
from typing import List, Optional

from core.models import Doctor, Shift

DB_PATH = os.path.join("data", "roster.db")


# -------------------------------------------------------
#  CONNECTION + INITIALISATION
# -------------------------------------------------------

def get_connection():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # -----------------------------
    # DOCTORS
    # -----------------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS doctors (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            level TEXT NOT NULL,
            firm INTEGER,
            contract_hours_per_month INTEGER NOT NULL,
            min_shifts_per_month INTEGER NOT NULL,
            max_shifts_per_month INTEGER NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        )
        """
    )

    # -----------------------------
    # SHIFTS
    # -----------------------------
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

    # -----------------------------
    # LEAVE
    # -----------------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS leave_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            leave_type TEXT NOT NULL,
            reason TEXT,
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        )
        """
    )

    # -----------------------------
    # ASSIGNMENTS
    # -----------------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_id TEXT NOT NULL,
            shift_id INTEGER NOT NULL,
            FOREIGN KEY (doctor_id) REFERENCES doctors(id),
            FOREIGN KEY (shift_id) REFERENCES shifts(id)
        )
        """
    )

    conn.commit()
    conn.close()


# -------------------------------------------------------
# DOCTORS
# -------------------------------------------------------

def _generate_doctor_id(name: str) -> str:
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

    doctor_id = _generate_doctor_id(name)

    cur.execute(
        """
        INSERT INTO doctors (id, name, level, firm,
                             contract_hours_per_month,
                             min_shifts_per_month,
                             max_shifts_per_month,
                             active)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (doctor_id, name, level, firm,
         contract_hours, min_shifts, max_shifts)
    )

    conn.commit()
    conn.close()

    return Doctor(
        id=doctor_id,
        name=name,
        level=level,
        firm=firm,
        contract_hours_per_month=contract_hours,
        min_shifts_per_month=min_shifts,
        max_shifts_per_month=max_shifts,
        active=True
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

    result = []
    for r in rows:
        result.append(
            Doctor(
                id=r["id"],
                name=r["name"],
                level=r["level"],
                firm=r["firm"],
                contract_hours_per_month=r["contract_hours_per_month"],
                min_shifts_per_month=r["min_shifts_per_month"],
                max_shifts_per_month=r["max_shifts_per_month"],
                active=bool(r["active"])
            )
        )
    return result


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
        SET contract_hours_per_month = ?,
            min_shifts_per_month = ?,
            max_shifts_per_month = ?
        WHERE id = ?
        """,
        (contract_hours, min_shifts, max_shifts, external_id)
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
    Accepts list of dicts:
      date, start_time, end_time, duration_hours,
      min_doctors, max_doctors, is_weekend
    """
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM shifts")

    for s in shift_rows:
        cur.execute(
            """
            INSERT INTO shifts (
                date, start_time, end_time,
                duration_hours, min_doctors,
                max_doctors, is_weekend
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

    shifts = []
    for r in rows:
        shifts.append(
            Shift(
                id=r["id"],
                start=datetime.fromisoformat(r["start_time"]),
                end=datetime.fromisoformat(r["end_time"]),
                duration_hours=r["duration_hours"],
                min_doctors=r["min_doctors"],
                max_doctors=r["max_doctors"],
                is_weekend=bool(r["is_weekend"])
            )
        )
    return shifts


# -------------------------------------------------------
# LEAVE
# -------------------------------------------------------

def create_leave(
    doctor_id: str,
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
        (doctor_id, start_date, end_date, leave_type, reason)
        VALUES (?, ?, ?, ?, ?)
        """,
        (doctor_id,
         start_date.date().isoformat(),
         end_date.date().isoformat(),
         leave_type,
         reason)
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


# -------------------------------------------------------
# ASSIGNMENTS
# -------------------------------------------------------

def save_assignments(assignments):
    """
    assignments: list of dicts:
      { "doctor_id": ..., "shift_id": ... }
    """
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM assignments")

    for a in assignments:
        cur.execute(
            """
            INSERT INTO assignments (doctor_id, shift_id)
            VALUES (?, ?)
            """,
            (a["doctor_id"], a["shift_id"])
        )

    conn.commit()
    conn.close()


def load_assignments():
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM assignments ORDER BY shift_id")
    rows = cur.fetchall()
    conn.close()

    return [
        {"doctor_id": r["doctor_id"], "shift_id": r["shift_id"]}
        for r in rows
    ]
