"""
seed_data.py — Populate the database with realistic sample sessions
and attendance records for testing and demo purposes.

Run AFTER the app has been started once (to create the DB schema):
    python seed_data.py
"""

import sqlite3
import os
import sys
import uuid
import random
from datetime import datetime, timedelta, date

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'attendance.db')

SUBJECTS = [
    'Data Structures',
    'Computer Networks',
    'Operating Systems',
    'Database Management',
    'Machine Learning',
]

def seed():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    teacher_id = conn.execute("SELECT id FROM teacher LIMIT 1").fetchone()['id']
    students   = conn.execute("SELECT id FROM student").fetchall()
    student_ids = [s['id'] for s in students]

    print(f"[Seed] Teacher ID: {teacher_id}")
    print(f"[Seed] Students: {student_ids}")

    # Generate 40 sessions over the last 30 days
    today     = date.today()
    sessions  = []
    times     = [('08:00', '09:00'), ('09:00', '10:00'),
                 ('10:15', '11:15'), ('11:15', '12:15'),
                 ('14:00', '15:00'), ('15:00', '16:00')]

    for day_offset in range(30, 0, -1):
        d = today - timedelta(days=day_offset)
        if d.weekday() >= 5:  # skip weekends
            continue

        num_classes = random.randint(2, 4)
        used_times  = random.sample(times, min(num_classes, len(times)))

        for subject in random.sample(SUBJECTS, num_classes):
            t = random.choice(used_times)
            tok = str(uuid.uuid4())

            try:
                conn.execute(
                    """INSERT INTO session (teacher_id, subject, qr_data, date, start_time, end_time)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (teacher_id, subject, tok, d.isoformat(), t[0], t[1])
                )
                conn.commit()
                session_id = conn.execute(
                    "SELECT id FROM session WHERE qr_data = ?", (tok,)
                ).fetchone()['id']
                sessions.append((session_id, d, subject))
            except Exception as e:
                pass  # duplicate token, skip

    print(f"[Seed] Created {len(sessions)} sessions")

    # Mark attendance — each student has individual attendance patterns
    # Some students have good attendance, some declining, some at-risk
    patterns = {
        0: 0.92,  # Very good
        1: 0.85,
        2: 0.78,
        3: 0.72,  # Borderline
        4: 0.65,  # At risk
        5: 0.58,  # Critical
        6: 0.50,
        7: 0.45,
    }

    att_count = 0
    for i, sid in enumerate(student_ids):
        base_prob = patterns.get(i, 0.75)

        for (sess_id, sess_date, subject) in sessions:
            # Simulate irregular patterns for some students
            prob = base_prob
            if i >= 4 and sess_date.weekday() == 0:  # at-risk students skip Mondays
                prob *= 0.4
            if i >= 5 and subject == 'Machine Learning':  # selective absence
                prob *= 0.3

            # Recent decline for student index 3
            days_ago = (today - sess_date).days
            if i == 3 and days_ago < 10:
                prob *= 0.4

            if random.random() < prob:
                # Random arrival time within session
                h, m = map(int, '08:00'.split(':'))
                arrival_offset = random.randint(0, 50)
                arr_time = f"{h + arrival_offset // 60:02d}:{(m + arrival_offset) % 60:02d}:00"

                status = 'late' if arrival_offset > 40 else 'present'

                try:
                    conn.execute(
                        """INSERT INTO attendance (student_id, session_id, date, time, status)
                           VALUES (?, ?, ?, ?, ?)""",
                        (sid, sess_id, sess_date.isoformat(), arr_time, status)
                    )
                    att_count += 1
                except Exception:
                    pass  # duplicate, skip

    conn.commit()
    conn.close()
    print(f"[Seed] Inserted {att_count} attendance records")
    print("[Seed] Done! You can now run the app and see populated data.")


if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        print("[Seed] Database not found. Start the app once first: python backend/app.py")
        sys.exit(1)
    seed()
