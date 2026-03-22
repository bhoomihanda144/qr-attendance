"""
Analytics Blueprint
Attendance analytics, reports, and ML-based predictions.
Integrates with ml/predictor.py for scikit-learn models.
"""

from flask import Blueprint, request, jsonify, session
from database import get_db
import pandas as pd
import sys, os

# Add parent directory to path for ml module
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from ml.predictor import AttendancePredictor

analytics_bp = Blueprint('analytics', __name__)
predictor    = AttendancePredictor()


def _require_teacher():
    if session.get('user_role') != 'teacher':
        return jsonify({'error': 'Teacher access required'}), 403
    return None


# ── Dashboard Summary ───────────────────────────────────────────────────────────

@analytics_bp.route('/dashboard', methods=['GET'])
def dashboard():
    err = _require_teacher()
    if err:
        return err

    db         = get_db()
    teacher_id = session['user_id']

    # Totals
    total_sessions  = db.execute(
        "SELECT COUNT(*) as c FROM session WHERE teacher_id = ?", (teacher_id,)
    ).fetchone()['c']

    total_students  = db.execute("SELECT COUNT(*) as c FROM student").fetchone()['c']

    total_att_today = db.execute(
        """SELECT COUNT(*) as c FROM attendance a
           JOIN session s ON s.id = a.session_id
           WHERE s.teacher_id = ? AND a.date = date('now')""",
        (teacher_id,)
    ).fetchone()['c']

    avg_pct = db.execute(
        """SELECT ROUND(AVG(pct), 1) as avg FROM (
               SELECT st.id,
                      COUNT(a.id) * 100.0 / NULLIF(COUNT(DISTINCT s.id), 0) as pct
               FROM student st
               CROSS JOIN session s
               LEFT JOIN attendance a
                 ON a.student_id = st.id AND a.session_id = s.id
               WHERE s.teacher_id = ?
               GROUP BY st.id
           )""",
        (teacher_id,)
    ).fetchone()['avg'] or 0

    # Attendance trend — last 14 days
    trend = db.execute(
        """SELECT a.date, COUNT(*) as count
           FROM attendance a
           JOIN session s ON s.id = a.session_id
           WHERE s.teacher_id = ?
             AND a.date >= date('now', '-14 days')
           GROUP BY a.date
           ORDER BY a.date""",
        (teacher_id,)
    ).fetchall()

    # Per-subject avg
    subject_stats = db.execute(
        """SELECT s.subject,
                  COUNT(DISTINCT s.id) as sessions,
                  COUNT(a.id)          as total_marked,
                  ROUND(COUNT(a.id) * 100.0 /
                        NULLIF(COUNT(DISTINCT s.id) *
                               (SELECT COUNT(*) FROM student), 0), 1) as avg_pct
           FROM session s
           LEFT JOIN attendance a ON a.session_id = s.id
           WHERE s.teacher_id = ?
           GROUP BY s.subject""",
        (teacher_id,)
    ).fetchall()

    return jsonify({
        'total_sessions':   total_sessions,
        'total_students':   total_students,
        'attendance_today': total_att_today,
        'avg_percentage':   round(avg_pct, 1),
        'trend':            [dict(r) for r in trend],
        'subject_stats':    [dict(r) for r in subject_stats]
    })


# ── Per-student analytics ───────────────────────────────────────────────────────

@analytics_bp.route('/students', methods=['GET'])
def student_analytics():
    err = _require_teacher()
    if err:
        return err

    db         = get_db()
    teacher_id = session['user_id']

    rows = db.execute(
        """SELECT st.id, st.name, st.usn,
                  COUNT(DISTINCT s.id) as total_sessions,
                  COUNT(a.id)          as attended,
                  ROUND(COUNT(a.id) * 100.0 /
                        NULLIF(COUNT(DISTINCT s.id), 0), 1) as percentage
           FROM student st
           CROSS JOIN session s
           LEFT JOIN attendance a
             ON a.student_id = st.id AND a.session_id = s.id
           WHERE s.teacher_id = ?
           GROUP BY st.id
           ORDER BY percentage ASC""",
        (teacher_id,)
    ).fetchall()

    return jsonify([dict(r) for r in rows])


# ── ML Predictions ──────────────────────────────────────────────────────────────

@analytics_bp.route('/predict', methods=['GET'])
def predict_at_risk():
    """
    Use trained ML model to predict which students are at risk
    of falling below the 75% attendance threshold.
    """
    err = _require_teacher()
    if err:
        return err

    db         = get_db()
    teacher_id = session['user_id']

    # Fetch raw attendance data for ML
    rows = db.execute(
        """SELECT st.id as student_id, st.name, st.usn,
                  s.subject, s.date,
                  CASE WHEN a.id IS NOT NULL THEN 1 ELSE 0 END as present
           FROM student st
           CROSS JOIN session s
           LEFT JOIN attendance a
             ON a.student_id = st.id AND a.session_id = s.id
           WHERE s.teacher_id = ?
           ORDER BY st.id, s.date""",
        (teacher_id,)
    ).fetchall()

    if not rows:
        return jsonify({'predictions': [], 'message': 'No data available'})

    df          = pd.DataFrame([dict(r) for r in rows])
    predictions = predictor.predict_at_risk(df)

    return jsonify({'predictions': predictions})


# ── Anomaly / Irregular Pattern Detection ──────────────────────────────────────

@analytics_bp.route('/anomalies', methods=['GET'])
def detect_anomalies():
    """
    Detect students with irregular attendance patterns:
    - Sudden drops in attendance
    - Long consecutive absences
    - Selective absence (missing specific days/subjects)
    """
    err = _require_teacher()
    if err:
        return err

    db         = get_db()
    teacher_id = session['user_id']

    rows = db.execute(
        """SELECT st.id as student_id, st.name, st.usn,
                  s.subject, s.date,
                  CASE WHEN a.id IS NOT NULL THEN 1 ELSE 0 END as present
           FROM student st
           CROSS JOIN session s
           LEFT JOIN attendance a
             ON a.student_id = st.id AND a.session_id = s.id
           WHERE s.teacher_id = ?
           ORDER BY st.id, s.date""",
        (teacher_id,)
    ).fetchall()

    if not rows:
        return jsonify({'anomalies': []})

    df        = pd.DataFrame([dict(r) for r in rows])
    anomalies = predictor.detect_anomalies(df)

    return jsonify({'anomalies': anomalies})


# ── Student Self Analytics ──────────────────────────────────────────────────────

@analytics_bp.route('/my-stats', methods=['GET'])
def my_stats():
    if session.get('user_role') != 'student':
        return jsonify({'error': 'Student access required'}), 403

    db         = get_db()
    student_id = session['user_id']

    subject_rows = db.execute(
        """SELECT s.subject,
                  COUNT(DISTINCT s.id) as total,
                  COUNT(a.id)          as attended,
                  ROUND(COUNT(a.id) * 100.0 / NULLIF(COUNT(DISTINCT s.id), 0), 1) as pct
           FROM session s
           LEFT JOIN attendance a
             ON a.session_id = s.id AND a.student_id = ?
           GROUP BY s.subject
           ORDER BY s.subject""",
        (student_id,)
    ).fetchall()

    trend = db.execute(
        """SELECT a.date, COUNT(*) as count
           FROM attendance a
           WHERE a.student_id = ?
             AND a.date >= date('now', '-30 days')
           GROUP BY a.date
           ORDER BY a.date""",
        (student_id,)
    ).fetchall()

    return jsonify({
        'subject_stats': [dict(r) for r in subject_rows],
        'trend':         [dict(r) for r in trend]
    })
