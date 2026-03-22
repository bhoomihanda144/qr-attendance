<<<<<<< HEAD
# 🎓 SmartAttend — QR-Based Smart Attendance System

A full-stack, AI-powered attendance management system for colleges.
Built with **Flask**, **SQLite**, **scikit-learn**, and a modern vanilla JS frontend.

---

## 📁 Project Structure

```
qr_attendance/
├── backend/
│   ├── app.py                  # Flask app factory & entry point
│   ├── database.py             # SQLite init, schema, helpers
│   ├── routes/
│   │   ├── auth.py             # Teacher & student login/register
│   │   ├── sessions.py         # QR generation, session CRUD
│   │   ├── attendance.py       # Attendance marking & queries
│   │   └── analytics.py        # Reports & ML endpoints
│   └── ml/
│       └── predictor.py        # Scikit-learn models (GBM + DBSCAN)
├── frontend/
│   ├── templates/
│   │   └── index.html          # Single-page app shell
│   └── static/
│       ├── css/style.css       # Full design system
│       ├── js/
│       │   ├── api.js          # Fetch wrapper
│       │   ├── app.js          # Router & shared utilities
│       │   ├── auth.js         # Login/register logic
│       │   ├── teacher.js      # Teacher dashboard
│       │   └── student.js      # Student dashboard + QR scanner
│       └── qr_codes/           # Generated QR images (auto-created)
├── database/
│   └── attendance.db           # SQLite DB (auto-created on first run)
├── requirements.txt
├── seed_data.py                # Populate sample sessions & attendance
└── README.md
```

---

## ⚡ Quick Setup

### 1. Clone / extract the project
```bash
cd qr_attendance
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Flask server
```bash
python backend/app.py
```
The app auto-creates the SQLite database with **sample teachers and students** on first run.

### 5. (Optional) Seed realistic session data
Open a second terminal with the venv active:
```bash
python seed_data.py
```
This creates ~40 sessions across the last 30 days with varied attendance patterns, perfect for testing the AI predictions.

### 6. Open the app
Visit **http://localhost:5000** in your browser.

---

## 🔑 Demo Credentials

### Teachers
| Name | Email | Password |
|------|-------|----------|
| Dr. Ramesh Kumar | ramesh@college.edu | teacher123 |
| Prof. Anita Sharma | anita@college.edu | teacher123 |

### Students
| Name | USN | Password |
|------|-----|----------|
| Arjun Mehta | 1RV21CS001 | student123 |
| Priya Nair | 1RV21CS002 | student123 |
| Rohan Das | 1RV21CS003 | student123 |
| Sneha Patel | 1RV21CS004 | student123 |
| Vikram Singh | 1RV21CS005 | student123 |
| Kavya Reddy | 1RV21CS006 | student123 |
| Aditya Joshi | 1RV21CS007 | student123 |
| Meera Krishnan | 1RV21CS008 | student123 |

---

## 🔄 Demo Workflow

### Teacher Flow
1. Login at **http://localhost:5000** → Teacher
2. **New Session** → Enter subject, date, time → Click "Generate QR Code"
3. The QR image is displayed — share it with students or print it
4. View **My Sessions** to see all created sessions
5. Check **Attendance** tab to filter records by subject/date
6. Visit **Analytics** to see per-student attendance percentages
7. Click **AI Insights → Run Analysis** to see ML-based risk predictions

### Student Flow
1. Login → Student
2. **Scan QR** → Click "Start Camera" → Point at the QR code
   - Or paste the QR token in the manual entry field
3. Attendance is validated against the session time window
4. View **My Attendance** for full history
5. Check **My Stats** for subject-wise charts and percentage

---

## 🤖 AI/ML Module Explained

File: `backend/ml/predictor.py`

### Features Used
| Feature | Description |
|---------|-------------|
| `percentage` | Overall attendance % |
| `recent_pct` | Attendance in last 5 sessions |
| `max_abs_streak` | Longest consecutive absence run |
| `subject_variance` | Std deviation of subject-wise % |
| `days_since_last` | Days since last attendance |

### Models
- **Gradient Boosting Classifier** (`sklearn.ensemble`) — Predicts at-risk probability per student
- **DBSCAN Clustering** — Detects statistical outliers in attendance patterns
- **Rule-based layer** — Ensures predictions even with < 3 students (fallback heuristics)

### Risk Levels
| Level | Condition |
|-------|-----------|
| 🔴 High | Attendance < 60% OR probability > 0.75 |
| 🟠 Medium | Attendance < 75% OR probability > 0.45 |
| 🟢 Low | All conditions safe |

---

## 🗄️ Database Schema

```sql
teacher    (id, name, email, password, created_at)
student    (id, name, usn, email, password, created_at)
session    (id, teacher_id, subject, qr_data, date, start_time, end_time, created_at)
attendance (id, student_id, session_id, date, time, status)
           -- UNIQUE constraint on (student_id, session_id) prevents duplicates
           -- status: 'present' | 'late' (arrived after session end but within grace window)
```

---

## ⚙️ Key Implementation Details

### QR Generation
- Uses `python-qrcode` to encode a JSON payload: `{token, subject, date, start, end}`
- Token is a UUID stored in the `session` table
- QR image saved to `frontend/static/qr_codes/session_<id>.png`

### Attendance Validation
- Student can mark attendance **10 min before** to **15 min after** the session end
- Marking after the official end time → status = `late`
- Duplicate scan → `409 Conflict` response

### QR Scanning
- Uses `html5-qrcode` library (no OpenCV needed in browser)
- Falls back to manual token entry
- Camera access uses `facingMode: environment` (rear camera on mobile)

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10+, Flask 3.0, Flask-CORS |
| Database | SQLite (via Python sqlite3) |
| ML | scikit-learn (GBM + DBSCAN), pandas, numpy |
| QR Generation | python-qrcode, Pillow |
| Frontend | Vanilla JS (ES6+), HTML5, CSS3 |
| Charts | Chart.js 4.4 |
| QR Scanning | html5-qrcode |
| Fonts | Syne, DM Sans (Google Fonts) |
| Icons | Font Awesome 6 |
=======
# qr-attendance
>>>>>>> 213abe22453fd0c7df050bfe53b5c2fc78b80352
