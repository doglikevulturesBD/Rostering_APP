# core/database.py

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List

from core.models import Doctor, Shift


DB_PATH = Path("data/ed_roster.db")


# ==========================================================
# CONNECTION & INITIALIZATION
# ==========================================================

def get_connection() -> sqlite3.Connection:
    """Ensure DB folder exists and return a connection."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Creates tables if they do not exist."""
    conn = get_connection()
    cur = conn.cursor()

    # ------------------------- Doctors -------------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id TEXT UNIQUE,
            name TEXT NOT NULL,
            level TEXT NOT NULL,
            firm INTEGER,
            contract_hours INTEGER NOT NULL,
            min_shifts INTEGER NOT NULL,
            max_shifts INTEGER NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    # ------------------------- Shifts -------------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS shifts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            start TEXT NOT NULL,
            end TEXT NOT NULL,
            is_weekend INTEGER NOT NULL,
            is_night INTEGER NOT NULL,
            intensity INTEGER NOT NULL,
            min_doctors INTEGER NOT NULL,
            max_doctors INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    # ------------------------- Leave -------------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS leave_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_external_id TEXT NOT NULL,
            leave_type TEXT NOT NULL,        -- "annual" or "sick"
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            reason TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (doctor_external_id) REFERENCES doctors(external_id)
        )
        """
    )

    # ------------------------- Preferences -------------------------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS doctor_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doctor_external_id TEXT NOT NULL,
            preference_type TEXT NOT NULL,   -- e.g. "avoid_nights", "prefer_early", "unavailable"
            start_date TEXT,
            end_date TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (doctor_external_id) REFERENCES doctors(external_id)
        )
        """
    )

    conn.commit()
    conn.close()


# ==========================================================
# DOCTOR HELPERS
# ==========================================================

def _row_to_doctor(row: sqlite3.Row) -> Doctor:
    return Doctor(
        id=row["external_id"],
        name=row["name"],
        level=row["level"],
        firm=row["firm"],
        contract_hours_per_month=row["contract_hours"],
        min_shifts_per_month=row["min_shifts"],
        max_shifts_per_month=row["max_shifts"],
    )


def create_doctor(name, level, firm, contract_hours, min_shifts, max_shifts) -> Doctor:
    """Create a doctor and return the object."""
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()

    # Insert placeholder external_id first
    cur.execute(
        """
        INSERT INTO doctors 
        (external_id, name, level, firm, contract_hours, min_shifts, max_shifts,
         active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        """,
        ("", name, level, firm, contract_hours, min_shifts, max_shifts, now, now),
    )

    new_id = cur.lastrowid
    external_id = f"D{new_id:02d}"

    # Set correct external_id
    cur.execute(
        "UPDATE doctors SET external_id=?, updated_at=? WHERE id=?",
        (external_id, now, new_id),
    )

    conn.commit()
    conn.close()

    return Doctor(
        id=external_id,
        name=name,
        level=level,
        firm=firm,
        contract_hours_per_month=contract_hours,
        min_shifts_per_month=min_shifts,
        max_shifts_per_month=max_shifts,
    )


def get_all_doctors(active_only: bool = True) -> List[Doctor]:
    conn = get_connection()
    cur = conn.cursor()

    if active_only:
        cur.execute("SELECT * FROM doctors WHERE active=1 ORDER BY id")
    else:
        cur.execute("SELECT * FROM doctors ORDER BY id")

    rows = cur.fetchall()
    conn.close()
    return [_row_to_doctor(r) for r in rows]


def update_doctor_hours_and_shifts(external_id, contract_hours, min_shifts, max_shifts):
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()

    cur.execute(
        """
        UPDATE doctors
        SET contract_hours=?, min_shifts=?, max_shifts=?, updated_at=?
        WHERE external_id=?
        """,
        (contract_hours, min_shifts, max_shifts, now, external_id),
    )

    conn.commit()
    conn.close()


def deactivate_doctor(external_id):
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()

    cur.execute(
        "UPDATE doctors SET active=0, updated_at=? WHERE external_id=?",
        (now, external_id),
    )

    conn.commit()
    conn.close()


# ==========================================================
# SHIFT HELPERS
# ==========================================================

def delete_all_shifts():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM shifts")
    conn.commit()
    conn.close()


def save_shifts(shifts: List[Shift]):
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()

    for s in shifts:
        cur.execute(
            """
            INSERT OR REPLACE INTO shifts
            (id, name, start, end, is_weekend, is_night,
             intensity, min_doctors, max_doctors, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                s.id,
                s.name,
                s.start.isoformat(),
                s.end.isoformat(),
                1 if s.is_weekend else 0,
                1 if s.is_night else 0,
                s.intensity,
                s.min_doctors,
                s.max_doctors,
                now,
            ),
        )

    conn.commit()
    conn.close()


def load_shifts() -> List[Shift]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM shifts ORDER BY start")
    rows = cur.fetchall()
    conn.close()
    return [Shift.from_dict(dict(r)) for r in rows]


# ==========================================================
# LEAVE HELPERS
# ==========================================================

def create_leave_request(doctor_id, leave_type, start_date, end_date, reason=""):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO leave_requests
        (doctor_external_id, leave_type, start_date, end_date, reason, created_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
        """,
        (doctor_id, leave_type, start_date, end_date, reason),
    )

    conn.commit()
    conn.close()


def get_leave_for_doctor(doctor_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM leave_requests WHERE doctor_external_id=? ORDER BY start_date",
        (doctor_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_all_leave():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM leave_requests ORDER BY start_date")
    rows = cur.fetchall()
    conn.close()
    return rows


def delete_leave(leave_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM leave_requests WHERE id=?", (leave_id,))
    conn.commit()
    conn.close()


# ==========================================================
# PREFERENCES HELPERS
# ==========================================================

def create_preference(doctor_id, preference_type, start_date, end_date, notes=""):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO doctor_preferences
        (doctor_external_id, preference_type, start_date, end_date, notes, created_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
        """,
        (doctor_id, preference_type, start_date, end_date, notes),
    )

    conn.commit()
    conn.close()


def get_preferences_for_doctor(doctor_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM doctor_preferences
        WHERE doctor_external_id=?
        ORDER BY start_date
        """,
        (doctor_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_all_preferences():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM doctor_preferences ORDER BY start_date")
    rows = cur.fetchall()
    conn.close()
    return rows


def delete_preference(pref_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM doctor_preferences WHERE id=?", (pref_id,))
    conn.commit()
    conn.close()


