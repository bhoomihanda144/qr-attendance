"""
Auth Blueprint
Handles teacher & student registration, login, and logout.
"""

from flask import Blueprint, request, jsonify, session
from database import get_db
import hashlib

auth_bp = Blueprint('auth', __name__)


def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


# ── Teacher Auth ────────────────────────────────────────────────────────────────

@auth_bp.route('/teacher/register', methods=['POST'])
def teacher_register():
    data = request.get_json()
    name, email, password = data.get('name'), data.get('email'), data.get('password')

    if not all([name, email, password]):
        return jsonify({'error': 'All fields are required'}), 400

    db = get_db()
    try:
        db.execute(
            "INSERT INTO teacher (name, email, password) VALUES (?, ?, ?)",
            (name, email, _hash(password))
        )
        db.commit()
        return jsonify({'message': 'Teacher registered successfully'}), 201
    except Exception as e:
        return jsonify({'error': 'Email already exists'}), 409


@auth_bp.route('/teacher/login', methods=['POST'])
def teacher_login():
    data = request.get_json()
    email, password = data.get('email'), data.get('password')

    db = get_db()
    teacher = db.execute(
        "SELECT * FROM teacher WHERE email = ? AND password = ?",
        (email, _hash(password))
    ).fetchone()

    if not teacher:
        return jsonify({'error': 'Invalid credentials'}), 401

    # Store session
    session['user_id']   = teacher['id']
    session['user_role'] = 'teacher'
    session['user_name'] = teacher['name']

    return jsonify({
        'message': 'Login successful',
        'user': {'id': teacher['id'], 'name': teacher['name'],
                 'email': teacher['email'], 'role': 'teacher'}
    })


# ── Student Auth ────────────────────────────────────────────────────────────────

@auth_bp.route('/student/register', methods=['POST'])
def student_register():
    data = request.get_json()
    name     = data.get('name')
    usn      = data.get('usn')
    email    = data.get('email')
    password = data.get('password')

    if not all([name, usn, email, password]):
        return jsonify({'error': 'All fields are required'}), 400

    db = get_db()
    try:
        db.execute(
            "INSERT INTO student (name, usn, email, password) VALUES (?, ?, ?, ?)",
            (name, usn.upper(), email, _hash(password))
        )
        db.commit()
        return jsonify({'message': 'Student registered successfully'}), 201
    except Exception:
        return jsonify({'error': 'USN or email already exists'}), 409


@auth_bp.route('/student/login', methods=['POST'])
def student_login():
    data = request.get_json()
    usn_or_email = data.get('usn_or_email', '')
    password     = data.get('password')

    db = get_db()
    student = db.execute(
        """SELECT * FROM student
           WHERE (usn = ? OR email = ?) AND password = ?""",
        (usn_or_email.upper(), usn_or_email, _hash(password))
    ).fetchone()

    if not student:
        return jsonify({'error': 'Invalid credentials'}), 401

    session['user_id']   = student['id']
    session['user_role'] = 'student'
    session['user_name'] = student['name']

    return jsonify({
        'message': 'Login successful',
        'user': {'id': student['id'], 'name': student['name'],
                 'usn': student['usn'], 'email': student['email'], 'role': 'student'}
    })


# ── Shared ──────────────────────────────────────────────────────────────────────

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out'})


@auth_bp.route('/me', methods=['GET'])
def me():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    return jsonify({
        'id':   session['user_id'],
        'name': session['user_name'],
        'role': session['user_role']
    })
