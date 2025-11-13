# core/database.py
import sqlite3
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from .models import Doctor

DB_PATH = Path("data/ed_roster.db")


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    cur = conn.cursor()

    # Doctors table – we can extend this later without breaking anything
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS doctors (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id     TEXT UNIQUE,          -- e.g. D01, D02...
            name            TEXT NOT NULL,
            level           TEXT NOT NULL,        -- MO, Reg, Consultant, ComServ
            firm            INTEGER,              -- optional
            contract_hours  INTEGER NOT NULL DEFAULT 175,
            min_shifts      INTEGER NOT NULL DEFAULT 16,
            max_shifts      INTEGER NOT NULL DEFAULT 18,
            active          INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        )
        """
    )

    # Shifts table
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




    
    # We'll add shifts, assignments, leave, etc. later
    conn.commit()
    conn.close()





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


def get_all_doctors(active_only: bool = True) -> List[Doctor]:
    conn = get_connection()
    cur = conn.cursor()
    if active_only:
        cur.execute("SELECT * FROM doctors WHERE active = 1 ORDER BY id")
    else:
        cur.execute("SELECT * FROM doctors ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return [_row_to_doctor(r) for r in rows]


def create_doctor(
    name: str,
    level: str,
    firm: Optional[int] = None,
    contract_hours: int = 175,
    min_shifts: int = 16,
    max_shifts: int = 18,
) -> Doctor:
    conn = get_connection()
    cur = conn.cursor()

    now = datetime.utcnow().isoformat()

    # insert first to get numeric id
    cur.execute(
        """
        INSERT INTO doctors
        (external_id, name, level, firm, contract_hours, min_shifts, max_shifts, active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        """,
        ("", name, level, firm, contract_hours, min_shifts, max_shifts, now, now),
    )
    db_id = cur.lastrowid

    # generate external_id like D01, D02,...
    external_id = f"D{db_id:02d}"
    cur.execute(
        "UPDATE doctors SET external_id = ?, updated_at = ? WHERE id = ?",
        (external_id, now, db_id),
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


def update_doctor_hours_and_shifts(
    external_id: str,
    contract_hours: int,
    min_shifts: int,
    max_shifts: int,
):
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute(
        """
        UPDATE doctors
        SET contract_hours = ?, min_shifts = ?, max_shifts = ?, updated_at = ?
        WHERE external_id = ?
        """,
        (contract_hours, min_shifts, max_shifts, now, external_id),
    )
    conn.commit()
    conn.close()


def deactivate_doctor(external_id: str):
    """Soft-delete; keep history."""
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute(
        "UPDATE doctors SET active = 0, updated_at = ? WHERE external_id = ?",
        (now, external_id),
    )
    conn.commit()
    conn.close()
