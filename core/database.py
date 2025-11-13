# core/database.py

# core/database.py

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List

from core.models import Doctor, Shift


DB_PATH = Path("data/ed_roster.db")


# ==========================================================
#  CONNECTION + INITIALIZATION
# ==========================================================

def get_connection() -> sqlite3.Connection:
    """Ensures DB folder exists and returns a connection."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes the doctors and shifts tables."""
    conn = get_connection()
    cur = conn.cursor()

    # -------------------------
    # Doctors Table
    # -------------------------
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

    # -------------------------
    # Shifts Table
    # -------------------------
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

    conn.commit()
    conn.close()


# ==========================================================
#  DOCTOR HELPERS
# ==========================================================

def _row_to_doctor(row: sqlite3.Row) -> Doctor:
    """Convert DB row → Doctor object."""
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
    """
    Creates a doctor and returns a full Doctor object.
    """
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()

    # Insert placeholder external_id until we have the DB auto-ID
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

    # Update external_id
    cur.execute(
        "UPDATE doctors SET external_id=?, updated_at=? WHERE id=?",
        (external_id, now, new_id),
    )

    conn.commit()
    conn.close()

    # Return Doctor object
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
    """Loads all doctors, ordered by DB ID."""
    conn = get_connection()
    cur = conn.cursor()

    if active_only:
        cur.execute("SELECT * FROM doctors WHERE active = 1 ORDER BY id")
    else:
        cur.execute("SELECT * FROM doctors ORDER BY id")

    rows = cur.fetchall()
    conn.close()

    return [_row_to_doctor(r) for r in rows]


def update_doctor_hours_and_shifts(external_id, contract_hours, min_shifts, max_shifts):
    """Update contract hours and shift requirements for a doctor."""
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()

    cur.execute(
        """
        UPDATE doctors
        SET contract_hours = ?,
            min_shifts = ?,
            max_shifts = ?,
            updated_at = ?
        WHERE external_id = ?
        """,
        (contract_hours, min_shifts, max_shifts, now, external_id),
    )

    conn.commit()
    conn.close()


def deactivate_doctor(external_id):
    """Soft-delete a doctor by marking them inactive."""
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()

    cur.execute(
        """
        UPDATE doctors
        SET active = 0,
            updated_at = ?
        WHERE external_id = ?
        """,
        (now, external_id),
    )

    conn.commit()
    conn.close()


# ==========================================================
#  SHIFT HELPERS
# ==========================================================

def delete_all_shifts():
    """Remove all shift entries."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM shifts")
    conn.commit()
    conn.close()


def save_shifts(shifts: List[Shift]):
    """Save a list of Shift objects into the DB (overwrite existing)."""
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
    """Load all shifts from DB and return as Shift objects."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM shifts ORDER BY start")
    rows = cur.fetchall()

    conn.close()

    return [Shift.from_dict(dict(r)) for r in rows]
