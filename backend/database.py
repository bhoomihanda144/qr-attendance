"""
Database Module — SQLite via Python's sqlite3
Handles init, connection management, and schema creation.
"""

import sqlite3
import os
from flask import g, current_app
import hashlib


# ── Connection helpers ──────────────────────────────────────────────────────────

def get_db():
    """Return (and cache) a DB connection for the current app context."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row   # rows behave like dicts
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


# ── Schema ──────────────────────────────────────────────────────────────────────

SCHEMA = """
-- Teachers
CREATE TABLE IF NOT EXISTS teacher (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    email      TEXT    NOT NULL UNIQUE,
    password   TEXT    NOT NULL,          -- SHA-256 hash
    created_at TEXT    DEFAULT (datetime('now'))
);

-- Students
CREATE TABLE IF NOT EXISTS student (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    usn        TEXT    NOT NULL UNIQUE,   -- University Serial Number
    email      TEXT    NOT NULL UNIQUE,
    password   TEXT    NOT NULL,          -- SHA-256 hash
    created_at TEXT    DEFAULT (datetime('now'))
);

-- Class Sessions
CREATE TABLE IF NOT EXISTS session (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL,
    subject    TEXT    NOT NULL,
    qr_data    TEXT    NOT NULL UNIQUE,   -- UUID token embedded in QR
    date       TEXT    NOT NULL,          -- YYYY-MM-DD
    start_time TEXT    NOT NULL,          -- HH:MM
    end_time   TEXT    NOT NULL,          -- HH:MM
    created_at TEXT    DEFAULT (datetime('now')),
    FOREIGN KEY (teacher_id) REFERENCES teacher(id)
);

-- Attendance Records
CREATE TABLE IF NOT EXISTS attendance (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    session_id INTEGER NOT NULL,
    date       TEXT    NOT NULL,
    time       TEXT    NOT NULL,
    status     TEXT    NOT NULL DEFAULT 'present',  -- present | absent | late
    UNIQUE (student_id, session_id),               -- prevent duplicates
    FOREIGN KEY (student_id) REFERENCES student(id),
    FOREIGN KEY (session_id) REFERENCES session(id)
);
"""

SAMPLE_DATA = """
-- Sample teacher  (password = 'teacher123')
INSERT OR IGNORE INTO teacher (name, email, password) VALUES
  ('Dr. Ramesh Kumar',   'ramesh@college.edu',  '{hash_t1}'),
  ('Prof. Anita Sharma', 'anita@college.edu',   '{hash_t2}');

-- Sample students  (password = 'student123')
INSERT OR IGNORE INTO student (name, usn, email, password) VALUES
  ('Arjun Mehta',    '1RV21CS001', 'arjun@student.edu',    '{hash_s}'),
  ('Priya Nair',     '1RV21CS002', 'priya@student.edu',    '{hash_s}'),
  ('Rohan Das',      '1RV21CS003', 'rohan@student.edu',    '{hash_s}'),
  ('Sneha Patel',    '1RV21CS004', 'sneha@student.edu',    '{hash_s}'),
  ('Vikram Singh',   '1RV21CS005', 'vikram@student.edu',   '{hash_s}'),
  ('Kavya Reddy',    '1RV21CS006', 'kavya@student.edu',    '{hash_s}'),
  ('Aditya Joshi',   '1RV21CS007', 'aditya@student.edu',  '{hash_s}'),
  ('Meera Krishnan', '1RV21CS008', 'meera@student.edu',   '{hash_s}');
"""


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def init_db(app):
    """Create tables and insert sample data if the DB is fresh."""
    app.teardown_appcontext(close_db)

    db_path = app.config['DATABASE']
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)

    # Insert sample data with hashed passwords
    sample = SAMPLE_DATA.format(
        hash_t1=_hash('teacher123'),
        hash_t2=_hash('teacher123'),
        hash_s=_hash('student123')
    )
    conn.executescript(sample)
    conn.commit()
    conn.close()
    print(f"[DB] Initialised → {db_path}")
