"""
ML Module — Attendance Predictor & Anomaly Detector
Uses scikit-learn to:
  1. Predict students at risk of falling below 75% attendance
  2. Detect irregular attendance patterns via clustering
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, DBSCAN
from sklearn.pipeline import Pipeline
import warnings
warnings.filterwarnings('ignore')


THRESHOLD = 75.0   # Attendance % below which a student is "at risk"


class AttendancePredictor:
    """
    Encapsulates all ML logic.
    The model is trained on-the-fly each time (small dataset) so no
    pre-trained files are needed. For production, persist the model.
    """

    def __init__(self):
        # Gradient Boosting works well on small tabular datasets
        self.clf = Pipeline([
            ('scaler', StandardScaler()),
            ('model',  GradientBoostingClassifier(
                n_estimators=100, max_depth=3, random_state=42
            ))
        ])
        self._trained = False

    # ── Feature Engineering ─────────────────────────────────────────────────────

    def _build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Input df columns: student_id, name, usn, subject, date, present (0/1)
        Returns per-student feature matrix.
        """
        # Sort by student and date
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.sort_values(['student_id', 'date'])

        features = []
        for sid, grp in df.groupby('student_id'):
            total    = len(grp)
            attended = grp['present'].sum()
            pct      = (attended / total * 100) if total > 0 else 0

            # Recent trend: last 5 sessions
            recent       = grp.tail(5)['present']
            recent_pct   = recent.mean() * 100 if len(recent) > 0 else pct

            # Longest consecutive absence streak
            absences       = (grp['present'] == 0).astype(int)
            streaks        = absences * (absences.groupby(
                (absences != absences.shift()).cumsum()).cumcount() + 1
            )
            max_abs_streak = int(streaks.max()) if len(streaks) > 0 else 0

            # Subject variance (missing specific subjects)
            sub_pcts    = grp.groupby('subject')['present'].mean() * 100
            sub_var     = float(sub_pcts.std()) if len(sub_pcts) > 1 else 0.0

            # Days since last attendance
            last_att = grp[grp['present'] == 1]['date'].max()
            if pd.isnull(last_att):
                days_since_last = 999
            else:
                days_since_last = max(0, (grp['date'].max() - last_att).days)

            features.append({
                'student_id':       sid,
                'name':             grp['name'].iloc[0],
                'usn':              grp['usn'].iloc[0],
                'total_sessions':   int(total),
                'attended':         int(attended),
                'percentage':       round(pct, 1),
                'recent_pct':       round(recent_pct, 1),
                'max_abs_streak':   max_abs_streak,
                'subject_variance': round(sub_var, 2),
                'days_since_last':  int(days_since_last),
                'at_risk':          int(pct < THRESHOLD)
            })

        return pd.DataFrame(features)

    # ── Training ─────────────────────────────────────────────────────────────────

    FEATURE_COLS = [
        'total_sessions', 'attended', 'percentage',
        'recent_pct', 'max_abs_streak', 'subject_variance', 'days_since_last'
    ]

    def _train_if_needed(self, feat_df: pd.DataFrame):
        """Train using current data as training set (self-supervised)."""
        if len(feat_df) < 3:
            self._trained = False
            return

        X = feat_df[self.FEATURE_COLS].fillna(0)
        y = feat_df['at_risk']

        # Only train if we have both classes
        if y.nunique() < 2:
            self._trained = False
            return

        self.clf.fit(X, y)
        self._trained = True

    # ── Predict At-Risk ──────────────────────────────────────────────────────────

    def predict_at_risk(self, df: pd.DataFrame) -> list:
        """
        Returns a list of per-student dicts with:
          - risk_level: high / medium / low
          - probability: float
          - reason: human-readable explanation
        """
        feat_df = self._build_features(df)
        if feat_df.empty:
            return []

        self._train_if_needed(feat_df)

        results = []
        for _, row in feat_df.iterrows():
            pct       = row['percentage']
            recent    = row['recent_pct']
            streak    = row['max_abs_streak']
            days_last = row['days_since_last']

            # Rule-based probability when model isn't trained
            if self._trained:
                X_pred = pd.DataFrame([row[self.FEATURE_COLS]])
                prob   = float(self.clf.predict_proba(X_pred.fillna(0))[0][1])
            else:
                # Heuristic fallback
                prob = max(0.0, (THRESHOLD - pct) / THRESHOLD)
                if recent < pct - 10:  # declining trend
                    prob = min(1.0, prob + 0.2)

            # Determine risk level
            if   pct < 60  or prob > 0.75: risk = 'high'
            elif pct < 75  or prob > 0.45: risk = 'medium'
            else:                           risk = 'low'

            # Human-readable reason
            reasons = []
            if pct < THRESHOLD:
                sessions_needed = _sessions_needed(row['attended'], row['total_sessions'])
                reasons.append(
                    f"Currently at {pct}% (need {sessions_needed} more sessions to reach 75%)"
                )
            if recent < pct - 10:
                reasons.append(f"Declining trend: recent attendance {recent:.0f}%")
            if streak >= 3:
                reasons.append(f"Longest absence streak: {streak} sessions")
            if days_last > 7:
                reasons.append(f"No attendance in last {days_last} days")
            if row['subject_variance'] > 20:
                reasons.append("Irregular subject-wise attendance detected")

            results.append({
                'student_id':     int(row['student_id']),
                'name':           row['name'],
                'usn':            row['usn'],
                'percentage':     pct,
                'recent_pct':     recent,
                'total_sessions': int(row['total_sessions']),
                'attended':       int(row['attended']),
                'risk_level':     risk,
                'probability':    round(prob, 2),
                'reasons':        reasons or ['Attendance looks fine']
            })

        # Sort: high risk first
        order = {'high': 0, 'medium': 1, 'low': 2}
        results.sort(key=lambda x: (order[x['risk_level']], -x['probability']))
        return results

    # ── Anomaly Detection ────────────────────────────────────────────────────────

    def detect_anomalies(self, df: pd.DataFrame) -> list:
        """
        Uses DBSCAN clustering to find outlier attendance patterns.
        Also applies rule-based checks for specific irregularities.
        """
        feat_df = self._build_features(df)
        if feat_df.empty:
            return []

        anomalies = []

        # ── Rule-based checks ──────────────────────────────────────────────────
        for _, row in feat_df.iterrows():
            flags = []

            # Consecutive absences
            if row['max_abs_streak'] >= 4:
                flags.append({
                    'type':    'consecutive_absences',
                    'message': f"Missed {row['max_abs_streak']} consecutive sessions"
                })

            # Sharp decline: recent < overall by 20+
            if row['recent_pct'] < row['percentage'] - 20 and row['total_sessions'] > 5:
                flags.append({
                    'type':    'declining_trend',
                    'message': (
                        f"Sharp attendance drop: "
                        f"overall {row['percentage']:.0f}% vs recent {row['recent_pct']:.0f}%"
                    )
                })

            # Selective subject absence
            if row['subject_variance'] > 25:
                flags.append({
                    'type':    'selective_absence',
                    'message': "Highly irregular across subjects (possible selective bunking)"
                })

            if flags:
                anomalies.append({
                    'student_id': int(row['student_id']),
                    'name':       row['name'],
                    'usn':        row['usn'],
                    'percentage': row['percentage'],
                    'flags':      flags
                })

        # ── DBSCAN outlier detection on feature space ──────────────────────────
        if len(feat_df) >= 5:
            X = feat_df[['percentage', 'max_abs_streak', 'subject_variance']].fillna(0)
            scaler   = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            db_model = DBSCAN(eps=1.5, min_samples=2)
            labels   = db_model.fit_predict(X_scaled)

            outlier_ids = feat_df[labels == -1]['student_id'].tolist()

            # Tag DBSCAN outliers that aren't already flagged
            existing_ids = {a['student_id'] for a in anomalies}
            for sid in outlier_ids:
                if sid not in existing_ids:
                    row = feat_df[feat_df['student_id'] == sid].iloc[0]
                    anomalies.append({
                        'student_id': int(sid),
                        'name':       row['name'],
                        'usn':        row['usn'],
                        'percentage': row['percentage'],
                        'flags': [{
                            'type':    'statistical_outlier',
                            'message': 'Unusual attendance pattern detected by ML model'
                        }]
                    })

        return sorted(anomalies, key=lambda x: x['percentage'])


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _sessions_needed(attended: int, total: int, threshold: float = 75.0) -> int:
    """
    Calculate how many consecutive sessions the student must attend
    to reach the threshold.
    """
    needed = 0
    t = total
    a = attended
    while (a / max(t, 1) * 100) < threshold and needed < 200:
        a += 1
        t += 1
        needed += 1
    return needed
