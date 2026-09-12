"""SQLite data access layer mirroring the original Client/Session JPA entities."""
import sqlite3
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    # Running as a PyInstaller executable: __file__ resolves inside the
    # temporary bundle extraction dir, which doesn't persist between runs.
    # Store the database next to the .exe instead.
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

DB_PATH = BASE_DIR / "data" / "clients.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS client (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    date_of_birth TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    backstory TEXT
);

CREATE TABLE IF NOT EXISTS session (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES client(id),
    date TEXT NOT NULL,
    time TEXT,
    duration_minutes INTEGER,
    paid INTEGER NOT NULL DEFAULT 0,
    notes TEXT
);
"""


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
