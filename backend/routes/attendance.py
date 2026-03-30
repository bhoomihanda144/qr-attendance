"""
Attendance Blueprint
QR scan → validate → record attendance.
Prevents duplicates and enforces time-window validation.
"""

from flask import Blueprint, request, jsonify, session as flask_session
from database import get_db
from datetime import datetime, timedelta
import json

attendance_bp = Blueprint('attendance', __name__)


# ── Mark Attendance (QR Scan) ───────────────────────────────────────────────────

@attendance_bp.route('/mark', methods=['POST'])
def mark_attendance():
    """
    Student scans QR → frontend sends the decoded QR payload here.
    Validates: session exists, time window, not duplicate.
    """
    if flask_session.get('user_role') != 'student':
        return jsonify({'error': 'Student access required'}), 403

    data       = request.get_json()
    qr_payload = data.get('qr_payload')   # raw string from QR scan

    if not qr_payload:
        return jsonify({'error': 'QR payload missing'}), 400

    # ── Parse payload ──────────────────────────────────────────────────────────
    try:
        payload = json.loads(qr_payload)
        qr_token = payload['token']
    except (json.JSONDecodeError, KeyError):
        # Support plain token strings too
        qr_token = qr_payload.strip()

    db         = get_db()
    student_id = flask_session['user_id']

    # ── Find session ──────────────────────────────────────────────────────────
    sess = db.execute(
        "SELECT * FROM session WHERE qr_data = ?", (qr_token,)
    ).fetchone()

    if not sess:
        return jsonify({'error': 'Invalid QR code — session not found'}), 404

    # ── Time-window validation ─────────────────────────────────────────────────
    now          = datetime.now()
    session_date = sess['date']                         # YYYY-MM-DD
    start_str    = f"{session_date} {sess['start_time']}"
    end_str      = f"{session_date} {sess['end_time']}"

    fmt          = "%Y-%m-%d %H:%M"
    session_start = datetime.strptime(start_str, fmt)
    session_end   = datetime.strptime(end_str,   fmt)
    window_start  = session_start - timedelta(minutes=60)  # allow 60 min early
    window_end    = session_end   + timedelta(minutes=60)  # allow 60 min grace

    status = 'present'
    if now < window_start:
        return jsonify({'error': 'Session has not started yet'}), 400
    if now > window_end:
        return jsonify({'error': 'Session has already ended — attendance window closed'}), 400
    if now > session_end:
        status = 'late'   # arrived after official end but within grace window

    # ── Duplicate check ────────────────────────────────────────────────────────
    existing = db.execute(
        "SELECT id FROM attendance WHERE student_id = ? AND session_id = ?",
        (student_id, sess['id'])
    ).fetchone()

    if existing:
        return jsonify({'error': 'Attendance already marked for this session'}), 409

    # ── Record attendance ──────────────────────────────────────────────────────
    now_date = now.strftime('%Y-%m-%d')
    now_time = now.strftime('%H:%M:%S')

    db.execute(
        """INSERT INTO attendance (student_id, session_id, date, time, status)
           VALUES (?, ?, ?, ?, ?)""",
        (student_id, sess['id'], now_date, now_time, status)
    )
    db.commit()

    return jsonify({
        'message': f'Attendance marked as {status}',
        'status':  status,
        'subject': sess['subject'],
        'date':    now_date,
        'time':    now_time
    }), 201


# ── Student's Own Attendance ────────────────────────────────────────────────────

@attendance_bp.route('/my', methods=['GET'])
def my_attendance():
    if flask_session.get('user_role') != 'student':
        return jsonify({'error': 'Student access required'}), 403

    student_id = flask_session['user_id']
    subject    = request.args.get('subject')
    db         = get_db()

    query = """
        SELECT a.*, s.subject, s.date as session_date,
               s.start_time, s.end_time, t.name as teacher_name
        FROM attendance a
        JOIN session s ON s.id = a.session_id
        JOIN teacher t ON t.id = s.teacher_id
        WHERE a.student_id = ?
    """
    params = [student_id]
    if subject:
        query  += " AND s.subject = ?"
        params.append(subject)
    query += " ORDER BY s.date DESC, s.start_time DESC"

    rows = db.execute(query, params).fetchall()
    return jsonify([dict(r) for r in rows])


# ── Per-subject summary for a student ──────────────────────────────────────────

@attendance_bp.route('/summary/<int:student_id>', methods=['GET'])
def student_summary(student_id):
    db = get_db()

    rows = db.execute(
        """SELECT s.subject,
                  COUNT(DISTINCT s.id) as total_sessions,
                  COUNT(a.id)          as attended,
                  ROUND(COUNT(a.id) * 100.0 / NULLIF(COUNT(DISTINCT s.id), 0), 1) as percentage
           FROM session s
           LEFT JOIN attendance a
             ON a.session_id = s.id AND a.student_id = ?
           GROUP BY s.subject
           ORDER BY s.subject""",
        (student_id,)
    ).fetchall()

    return jsonify([dict(r) for r in rows])


# ── All attendance (teacher view) ───────────────────────────────────────────────

@attendance_bp.route('/all', methods=['GET'])
def all_attendance():
    if flask_session.get('user_role') != 'teacher':
        return jsonify({'error': 'Teacher access required'}), 403

    subject = request.args.get('subject')
    date    = request.args.get('date')
    db      = get_db()

    query = """
        SELECT a.*, st.name as student_name, st.usn,
               s.subject, s.date as session_date, s.start_time
        FROM attendance a
        JOIN student st ON st.id  = a.student_id
        JOIN session  s  ON s.id  = a.session_id
        WHERE s.teacher_id = ?
    """
    params = [flask_session['user_id']]

    if subject:
        query  += " AND s.subject = ?"
        params.append(subject)
    if date:
        query  += " AND s.date = ?"
        params.append(date)

    query += " ORDER BY s.date DESC, st.name"

    rows = db.execute(query, params).fetchall()
    return jsonify([dict(r) for r in rows])


# ── Subjects list ───────────────────────────────────────────────────────────────

@attendance_bp.route('/subjects', methods=['GET'])
def list_subjects():
    """Return distinct subjects — used for dropdowns."""
    db   = get_db()
    rows = db.execute("SELECT DISTINCT subject FROM session ORDER BY subject").fetchall()
    return jsonify([r['subject'] for r in rows])
