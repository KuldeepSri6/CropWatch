"""SQLite helpers for diagnosis history and treatment logs."""

from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Any

from app.config import get_settings


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS diagnoses (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    crop TEXT NOT NULL,
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS treatments (
    id TEXT PRIMARY KEY,
    diagnosis_id TEXT NOT NULL,
    treatment TEXT NOT NULL,
    date TEXT NOT NULL,
    FOREIGN KEY (diagnosis_id) REFERENCES diagnoses(id)
);
"""


def _connect(database_path: str | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with schema and foreign keys enabled."""
    path = database_path or get_settings().database_path
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(_SCHEMA_SQL)
    return connection


def init_db(database_path: str | None = None) -> None:
    """Create diagnoses and treatments tables if they do not exist."""
    with _connect(database_path):
        return


def save_diagnosis(record: dict[str, Any], database_path: str | None = None) -> None:
    """Persist a diagnosis response payload."""
    with _connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO diagnoses (id, created_at, crop, payload)
            VALUES (?, ?, ?, ?)
            """,
            (
                record["id"],
                record["created_at"],
                record["crop"],
                json.dumps(record),
            ),
        )


def list_diagnoses(
    limit: int = 20, database_path: str | None = None
) -> list[dict[str, Any]]:
    """Return the most recent diagnosis payloads."""
    with _connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT payload FROM diagnoses
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [json.loads(row["payload"]) for row in rows]


def diagnosis_exists(diagnosis_id: str, database_path: str | None = None) -> bool:
    """Return True if a diagnosis id is stored."""
    with _connect(database_path) as connection:
        row = connection.execute(
            "SELECT 1 FROM diagnoses WHERE id = ?",
            (diagnosis_id,),
        ).fetchone()
    return row is not None


def add_treatment(
    diagnosis_id: str,
    treatment: str,
    date: str,
    database_path: str | None = None,
) -> dict[str, str]:
    """Insert a treatment log row linked to a diagnosis."""
    treatment_id = str(uuid.uuid4())
    with _connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO treatments (id, diagnosis_id, treatment, date)
            VALUES (?, ?, ?, ?)
            """,
            (treatment_id, diagnosis_id, treatment, date),
        )
    return {
        "id": treatment_id,
        "diagnosis_id": diagnosis_id,
        "treatment": treatment,
        "date": date,
    }
