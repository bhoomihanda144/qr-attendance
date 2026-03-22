"""
Sessions Blueprint
QR code generation, session CRUD for teachers.
"""

from flask import Blueprint, request, jsonify, session, current_app, send_from_directory
from database import get_db
import uuid
import os
import qrcode
import json
from datetime import datetime

sessions_bp = Blueprint('sessions', __name__)


def _require_teacher():
    if session.get('user_role') != 'teacher':
        return jsonify({'error': 'Teacher access required'}), 403
    return None


# ── Create Session + QR ─────────────────────────────────────────────────────────

@sessions_bp.route('/create', methods=['POST'])
def create_session():
    err = _require_teacher()
    if err:
        return err

    data       = request.get_json()
    subject    = data.get('subject')
    date       = data.get('date')        # YYYY-MM-DD
    start_time = data.get('start_time')  # HH:MM
    end_time   = data.get('end_time')    # HH:MM
    teacher_id = session['user_id']

    if not all([subject, date, start_time, end_time]):
        return jsonify({'error': 'All fields required'}), 400

    # Unique token embedded in QR
    qr_token = str(uuid.uuid4())

    # Payload to encode in QR (JSON)
    qr_payload = json.dumps({
        'token':   qr_token,
        'subject': subject,
        'date':    date,
        'start':   start_time,
        'end':     end_time
    })

    db = get_db()
    db.execute(
        """INSERT INTO session (teacher_id, subject, qr_data, date, start_time, end_time)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (teacher_id, subject, qr_token, date, start_time, end_time)
    )
    db.commit()

    session_row = db.execute(
        "SELECT id FROM session WHERE qr_data = ?", (qr_token,)
    ).fetchone()
    session_id = session_row['id']

    # Generate QR image
    qr_filename = f"session_{session_id}.png"
    qr_path     = os.path.join(current_app.config['QR_FOLDER'], qr_filename)
    img = qrcode.make(qr_payload)
    img.save(qr_path)

    return jsonify({
        'message':    'Session created',
        'session_id': session_id,
        'qr_token':   qr_token,
        'qr_image':   f'/static/qr_codes/{qr_filename}'
    }), 201


# ── List Sessions ───────────────────────────────────────────────────────────────

@sessions_bp.route('/my', methods=['GET'])
def my_sessions():
    err = _require_teacher()
    if err:
        return err

    db   = get_db()
    rows = db.execute(
        """SELECT s.*, COUNT(a.id) as attendance_count
           FROM session s
           LEFT JOIN attendance a ON a.session_id = s.id
           WHERE s.teacher_id = ?
           GROUP BY s.id
           ORDER BY s.date DESC, s.start_time DESC""",
        (session['user_id'],)
    ).fetchall()

    sessions = []
    for r in rows:
        s = dict(r)
        s['qr_image'] = f"/static/qr_codes/session_{s['id']}.png"
        sessions.append(s)

    return jsonify(sessions)


@sessions_bp.route('/all', methods=['GET'])
def all_sessions():
    """Public endpoint — students need to see active sessions."""
    db   = get_db()
    rows = db.execute(
        """SELECT s.id, s.subject, s.date, s.start_time, s.end_time,
                  t.name as teacher_name
           FROM session s
           JOIN teacher t ON t.id = s.teacher_id
           ORDER BY s.date DESC, s.start_time DESC
           LIMIT 50"""
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@sessions_bp.route('/<int:session_id>', methods=['GET'])
def get_session(session_id):
    db  = get_db()
    row = db.execute(
        """SELECT s.*, t.name as teacher_name
           FROM session s JOIN teacher t ON t.id = s.teacher_id
           WHERE s.id = ?""",
        (session_id,)
    ).fetchone()
    if not row:
        return jsonify({'error': 'Session not found'}), 404
    s = dict(row)
    s['qr_image'] = f"/static/qr_codes/session_{s['id']}.png"
    return jsonify(s)


# ── Session Attendance List ─────────────────────────────────────────────────────

@sessions_bp.route('/<int:session_id>/attendance', methods=['GET'])
def session_attendance(session_id):
    err = _require_teacher()
    if err:
        return err

    db   = get_db()
    rows = db.execute(
        """SELECT a.*, st.name as student_name, st.usn
           FROM attendance a
           JOIN student st ON st.id = a.student_id
           WHERE a.session_id = ?
           ORDER BY a.time""",
        (session_id,)
    ).fetchall()
    return jsonify([dict(r) for r in rows])


# ── Delete Session ──────────────────────────────────────────────────────────────

@sessions_bp.route('/<int:session_id>', methods=['DELETE'])
def delete_session(session_id):
    err = _require_teacher()
    if err:
        return err

    db = get_db()
    db.execute("DELETE FROM attendance WHERE session_id = ?", (session_id,))
    db.execute(
        "DELETE FROM session WHERE id = ? AND teacher_id = ?",
        (session_id, session['user_id'])
    )
    db.commit()

    # Remove QR image
    qr_path = os.path.join(
        current_app.config['QR_FOLDER'], f"session_{session_id}.png"
    )
    if os.path.exists(qr_path):
        os.remove(qr_path)

    return jsonify({'message': 'Session deleted'})
