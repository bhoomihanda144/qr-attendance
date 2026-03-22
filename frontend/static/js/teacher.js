/**
 * teacher.js — Teacher dashboard logic
 * Handles sessions, attendance views, analytics, and AI predictions.
 */

let trendChart    = null;
let subjectChart  = null;

// ── Navigation ────────────────────────────────────────────────────

function teacherTab(tab) {
  document.querySelectorAll('#page-teacher .dash-tab').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('#page-teacher .nav-item').forEach(el => el.classList.remove('active'));

  document.getElementById(`tab-${tab}`).classList.add('active');

  const navMap = {
    'overview':     0, 'new-session': 1, 'sessions': 2,
    'attendance':   3, 'analytics':   4, 'predictions': 5
  };
  const navItems = document.querySelectorAll('#page-teacher .nav-item');
  if (navItems[navMap[tab]]) navItems[navMap[tab]].classList.add('active');

  const titles = {
    'overview': 'Overview', 'new-session': 'New Session',
    'sessions': 'My Sessions', 'attendance': 'Attendance',
    'analytics': 'Analytics', 'predictions': 'AI Insights'
  };
  document.getElementById('t-page-title').textContent = titles[tab] || tab;

  // Lazy-load data
  if (tab === 'sessions')    loadSessions();
  if (tab === 'attendance')  loadAttendance();
  if (tab === 'analytics')   loadStudentAnalytics();
  if (tab === 'new-session') setDefaultSessionDate();
}

function setDefaultSessionDate() {
  const today = new Date().toISOString().split('T')[0];
  const now   = new Date();
  const hhmm  = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;
  const end   = new Date(now.getTime() + 60*60*1000);
  const endHHMM = `${String(end.getHours()).padStart(2,'0')}:${String(end.getMinutes()).padStart(2,'0')}`;

  document.getElementById('s-date').value  = today;
  document.getElementById('s-start').value = hhmm;
  document.getElementById('s-end').value   = endHHMM;
}

// ── Dashboard ─────────────────────────────────────────────────────

async function loadDashboard() {
  try {
    const data = await API.dashboard();

    document.getElementById('stat-sessions').textContent = data.total_sessions;
    document.getElementById('stat-students').textContent = data.total_students;
    document.getElementById('stat-today').textContent    = data.attendance_today;
    document.getElementById('stat-avg').textContent      = `${data.avg_percentage}%`;

    renderTrendChart(data.trend);
    renderSubjectChart(data.subject_stats);
  } catch (err) {
    console.error('Dashboard error', err);
  }
}

function renderTrendChart(trend) {
  const ctx = document.getElementById('chart-trend').getContext('2d');
  if (trendChart) trendChart.destroy();

  trendChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: trend.map(t => formatDate(t.date)),
      datasets: [{
        label: 'Attendance Count',
        data:  trend.map(t => t.count),
        borderColor:     '#4f8ef7',
        backgroundColor: 'rgba(79,142,247,0.1)',
        borderWidth: 2.5,
        pointBackgroundColor: '#4f8ef7',
        pointRadius: 4,
        tension: 0.4,
        fill: true,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: '#9095b8' }, grid: { color: 'rgba(255,255,255,0.04)' } },
        y: { ticks: { color: '#9095b8' }, grid: { color: 'rgba(255,255,255,0.04)' }, beginAtZero: true }
      }
    }
  });
}

function renderSubjectChart(subjects) {
  const ctx = document.getElementById('chart-subjects').getContext('2d');
  if (subjectChart) subjectChart.destroy();

  const COLORS = ['#4f8ef7','#34d399','#fb923c','#a78bfa','#fbbf24','#f87171'];

  subjectChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: subjects.map(s => s.subject),
      datasets: [{
        data:            subjects.map(s => s.avg_pct || 0),
        backgroundColor: COLORS,
        borderWidth: 2,
        borderColor:     '#131626',
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: 'bottom', labels: { color: '#9095b8', boxWidth: 12 } }
      }
    }
  });
}

// ── Session Create ────────────────────────────────────────────────

async function createSession(e) {
  e.preventDefault();
  const body = {
    subject:    document.getElementById('s-subject').value,
    date:       document.getElementById('s-date').value,
    start_time: document.getElementById('s-start').value,
    end_time:   document.getElementById('s-end').value,
  };

  try {
    const data = await API.createSession(body);
    document.getElementById('qr-img').src = data.qr_image;
    document.getElementById('qr-result').classList.remove('hidden');
    showToast('Session created! QR code ready.', 'success');
    loadDashboard();
  } catch (err) {
    showToast(err.error || 'Failed to create session', 'error');
  }
}

function printQR() {
  const img = document.getElementById('qr-img');
  const w = window.open('');
  w.document.write(`<html><body style="text-align:center;padding:40px">
    <h2>SmartAttend QR Code</h2>
    <img src="${img.src}" style="width:300px"/>
    <p>Scan to mark attendance</p>
  </body></html>`);
  w.print();
}

function downloadQR() {
  const img = document.getElementById('qr-img');
  const a = document.createElement('a');
  a.href = img.src;
  a.download = 'session-qr.png';
  a.click();
}

// ── Sessions List ─────────────────────────────────────────────────

async function loadSessions() {
  try {
    const sessions = await API.mySessions();
    const tbody    = document.getElementById('sessions-tbody');

    if (!sessions.length) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text3);padding:32px">No sessions yet. Create your first one!</td></tr>';
      return;
    }

    tbody.innerHTML = sessions.map(s => `
      <tr>
        <td><strong>${s.subject}</strong></td>
        <td>${formatDate(s.date)}</td>
        <td>${s.start_time} – ${s.end_time}</td>
        <td><span class="badge badge-blue">${s.attendance_count} present</span></td>
        <td>
          <img src="${s.qr_image}" style="width:40px;height:40px;cursor:pointer;border-radius:4px;background:white;padding:2px"
               onclick="showQRModal('${s.qr_image}', '${s.subject}')"/>
        </td>
        <td>
          <button class="btn-secondary sm" onclick="viewSessionAttendance(${s.id})">
            <i class="fas fa-eye"></i>
          </button>
          <button class="btn-secondary sm" style="color:var(--red)" onclick="deleteSession(${s.id})">
            <i class="fas fa-trash"></i>
          </button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    showToast('Failed to load sessions', 'error');
  }
}

async function deleteSession(id) {
  if (!confirm('Delete this session and its attendance records?')) return;
  try {
    await API.deleteSession(id);
    showToast('Session deleted', 'info');
    loadSessions();
    loadDashboard();
  } catch (err) {
    showToast('Delete failed', 'error');
  }
}

function showQRModal(src, subject) {
  document.getElementById('modal-content').innerHTML = `
    <h3 style="font-family:var(--font-head);font-weight:700;margin-bottom:16px">${subject} — QR Code</h3>
    <div style="background:white;padding:16px;border-radius:12px;text-align:center;margin-bottom:16px">
      <img src="${src}" style="width:240px;height:240px"/>
    </div>
    <div style="display:flex;gap:10px;justify-content:center">
      <button class="btn-secondary" onclick="closeModal()">Close</button>
    </div>
  `;
  openModal();
}

async function viewSessionAttendance(sessionId) {
  try {
    const records = await API.sessionAttendance(sessionId);
    const rows    = records.length
      ? records.map(r => `
          <tr>
            <td>${r.student_name}</td>
            <td style="font-family:var(--font-mono);font-size:0.8rem">${r.usn}</td>
            <td>${r.time}</td>
            <td>${statusBadge(r.status)}</td>
          </tr>`).join('')
      : '<tr><td colspan="4" style="text-align:center;color:var(--text3);padding:24px">No attendance marked</td></tr>';

    document.getElementById('modal-content').innerHTML = `
      <h3 style="font-family:var(--font-head);font-weight:700;margin-bottom:16px">Session Attendance</h3>
      <table class="data-table">
        <thead><tr><th>Student</th><th>USN</th><th>Time</th><th>Status</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
      <div style="margin-top:16px;text-align:right">
        <button class="btn-secondary" onclick="closeModal()">Close</button>
      </div>
    `;
    openModal();
  } catch (err) {
    showToast('Failed to load attendance', 'error');
  }
}

// ── Attendance View ───────────────────────────────────────────────

async function loadSubjects() {
  try {
    const subjects = await API.subjects();
    const selects  = ['att-filter-subject', 's-subject-filter'];
    selects.forEach(id => {
      const sel = document.getElementById(id);
      if (!sel) return;
      const current = sel.value;
      sel.innerHTML = '<option value="">All Subjects</option>' +
        subjects.map(s => `<option value="${s}"${s===current?' selected':''}>${s}</option>`).join('');
    });
  } catch {}
}

async function loadAttendance() {
  const subject = document.getElementById('att-filter-subject')?.value || '';
  const date    = document.getElementById('att-filter-date')?.value    || '';

  try {
    const records = await API.allAttendance(subject, date);
    const tbody   = document.getElementById('attendance-tbody');

    if (!records.length) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text3);padding:32px">No records found</td></tr>';
      return;
    }

    tbody.innerHTML = records.map(r => `
      <tr>
        <td><strong>${r.student_name}</strong></td>
        <td style="font-family:var(--font-mono);font-size:0.8rem">${r.usn}</td>
        <td>${r.subject}</td>
        <td>${formatDate(r.session_date)}</td>
        <td>${r.time}</td>
        <td>${statusBadge(r.status)}</td>
      </tr>
    `).join('');
  } catch (err) {
    showToast('Failed to load attendance', 'error');
  }
}

function clearFilters() {
  document.getElementById('att-filter-subject').value = '';
  document.getElementById('att-filter-date').value    = '';
  loadAttendance();
}

// ── Student Analytics ─────────────────────────────────────────────

async function loadStudentAnalytics() {
  try {
    const students = await API.studentAnalytics();
    const tbody    = document.getElementById('analytics-tbody');

    tbody.innerHTML = students.map(st => {
      const pct   = st.percentage || 0;
      const cls   = pct >= 75 ? '' : pct >= 60 ? 'warn' : 'danger';
      const badge = pct >= 75
        ? '<span class="badge badge-green">Good</span>'
        : pct >= 60
          ? '<span class="badge badge-orange">At Risk</span>'
          : '<span class="badge badge-red">Critical</span>';

      return `
        <tr>
          <td><strong>${st.name}</strong></td>
          <td style="font-family:var(--font-mono);font-size:0.8rem">${st.usn}</td>
          <td>${st.total_sessions}</td>
          <td>${st.attended}</td>
          <td>
            <div class="pct-bar-wrap">
              <div class="pct-bar">
                <div class="pct-bar-fill ${cls}" style="width:${Math.min(pct,100)}%"></div>
              </div>
              <span style="font-weight:600;min-width:44px">${pct}%</span>
            </div>
          </td>
          <td>${badge}</td>
        </tr>`;
    }).join('');
  } catch (err) {
    showToast('Failed to load analytics', 'error');
  }
}

// ── AI Predictions ────────────────────────────────────────────────

async function loadPredictions() {
  const predList  = document.getElementById('predictions-list');
  const anomList  = document.getElementById('anomalies-list');

  predList.innerHTML  = '<div class="empty-state loading">Analysing attendance data…</div>';
  anomList.innerHTML  = '<div class="empty-state loading">Detecting patterns…</div>';

  try {
    const [predData, anomData] = await Promise.all([API.predictions(), API.anomalies()]);

    // Predictions
    const preds = predData.predictions || [];
    if (!preds.length) {
      predList.innerHTML = '<div class="empty-state">Not enough data for predictions yet</div>';
    } else {
      predList.innerHTML = preds.map(p => `
        <div class="prediction-item ${p.risk_level}">
          <div class="pred-header">
            <div>
              <div class="pred-name">${p.name}</div>
              <div class="pred-usn">${p.usn}</div>
            </div>
            <div>
              <div class="pred-pct" style="color:${p.risk_level==='high'?'var(--red)':p.risk_level==='medium'?'var(--orange)':'var(--green)'}">${p.percentage}%</div>
              <span class="badge ${p.risk_level==='high'?'badge-red':p.risk_level==='medium'?'badge-orange':'badge-green'}" style="font-size:0.7rem">${p.risk_level.toUpperCase()}</span>
            </div>
          </div>
          <div class="pred-reasons">
            ${p.reasons.map(r => `<div class="pred-reason">${r}</div>`).join('')}
          </div>
        </div>
      `).join('');
    }

    // Anomalies
    const anom = anomData.anomalies || [];
    if (!anom.length) {
      anomList.innerHTML = '<div class="empty-state">No anomalies detected</div>';
    } else {
      anomList.innerHTML = anom.map(a => `
        <div class="prediction-item medium">
          <div class="pred-header">
            <div>
              <div class="pred-name">${a.name}</div>
              <div class="pred-usn">${a.usn}</div>
            </div>
            <div class="pred-pct">${a.percentage}%</div>
          </div>
          <div class="pred-reasons">
            ${a.flags.map(f => `<div class="pred-reason">${f.message}</div>`).join('')}
          </div>
        </div>
      `).join('');
    }
  } catch (err) {
    predList.innerHTML = '<div class="empty-state">Analysis failed. Add more sessions first.</div>';
    anomList.innerHTML = '<div class="empty-state">—</div>';
  }
}

// ── Helpers ───────────────────────────────────────────────────────

function statusBadge(status) {
  const map = { present: 'badge-green', late: 'badge-orange', absent: 'badge-red' };
  return `<span class="badge ${map[status]||'badge-blue'}">${status}</span>`;
}

function formatDate(d) {
  if (!d) return '—';
  const date = new Date(d + 'T00:00:00');
  return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}
