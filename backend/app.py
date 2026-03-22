"""
QR-Based Smart Attendance System
Main Flask Application Entry Point
"""

from flask import Flask, jsonify
from flask_cors import CORS
from database import init_db
from routes.auth import auth_bp
from routes.sessions import sessions_bp
from routes.attendance import attendance_bp
from routes.analytics import analytics_bp
import os

def create_app():
    app = Flask(
        __name__,
        static_folder='../frontend/static',
        template_folder='../frontend/templates'
    )

    # ── Configuration ──────────────────────────────────────────────────────────
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'qr_attendance_secret_2024')
    app.config['DATABASE'] = os.path.join(os.path.dirname(__file__), '..', 'database', 'attendance.db')
    app.config['QR_FOLDER'] = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'static', 'qr_codes')
    app.config['SESSION_WINDOW_MINUTES'] = 30   # QR valid ± 30 min of session

    os.makedirs(app.config['QR_FOLDER'], exist_ok=True)

    # ── Extensions ─────────────────────────────────────────────────────────────
    CORS(app, supports_credentials=True)

    # ── Database ────────────────────────────────────────────────────────────────
    with app.app_context():
        init_db(app)

    # ── Blueprints ──────────────────────────────────────────────────────────────
    app.register_blueprint(auth_bp,       url_prefix='/api/auth')
    app.register_blueprint(sessions_bp,   url_prefix='/api/sessions')
    app.register_blueprint(attendance_bp, url_prefix='/api/attendance')
    app.register_blueprint(analytics_bp,  url_prefix='/api/analytics')

    # ── Serve frontend ──────────────────────────────────────────────────────────
    from flask import send_from_directory, render_template

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/<path:path>')
    def catch_all(path):
        return render_template('index.html')

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({'error': 'Internal server error'}), 500

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
