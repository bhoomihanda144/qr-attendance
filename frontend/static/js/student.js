/**
 * student.js — Student dashboard logic
 * QR scanning, attendance view, personal stats.
 */

let html5Scanner   = null;
let sTrendChart    = null;
let sSubjectChart  = null;

// ── Navigation ────────────────────────────────────────────────────

function studentTab(tab) {
  document.querySelectorAll('#page-student .dash-tab').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('#page-student .nav-item').forEach(el => el.classList.remove('active'));

  document.getElementById(`stab-${tab}`).classList.add('active');

  const navMap = { scan: 0, 'my-attendance': 1, 'my-stats': 2 };
  const navItems = document.querySelectorAll('#page-student .nav-item');
  if (navItems[navMap[tab]]) navItems[navMap[tab]].classList.add('active');

  const titles = { scan: 'Scan QR', 'my-attendance': 'My Attendance', 'my-stats': 'My Stats' };
  document.getElementById('s-page-title').textContent = titles[tab] || tab;

  // Stop scanner if navigating away
  if (tab !== 'scan' && html5Scanner) stopScanner();

  if (tab === 'my-attendance') loadMyAttendance();
  if (tab === 'my-stats')      loadMyStats();
}

// ── QR Scanner ────────────────────────────────────────────────────

function startScanner() {
  document.getElementById('btn-start-scan').classList.add('hidden');
  document.getElementById('btn-stop-scan').classList.remove('hidden');
  document.getElementById('scan-result').classList.add('hidden');

  html5Scanner = new Html5Qrcode('reader');
  const config = { fps: 10, qrbox: { width: 260, height: 260 } };

  html5Scanner.start(
    { facingMode: 'environment' },
    config,
    onScanSuccess,
    () => {}    // ignore frame errors
  ).catch(err => {
    showToast('Camera access denied. Use manual entry below.', 'error');
    stopScanner();
  });
}

function stopScanner() {
  if (html5Scanner) {
    html5Scanner.stop().catch(() => {});
    html5Scanner = null;
  }
  document.getElementById('btn-start-scan').classList.remove('hidden');
  document.getElementById('btn-stop-scan').classList.add('hidden');
}

async function onScanSuccess(decoded) {
  stopScanner();
  await submitAttendance(decoded);
}

// ── Manual Entry ──────────────────────────────────────────────────

async function markManual() {
  const token = document.getElementById('manual-token').value.trim();
  if (!token) { showToast('Enter a QR token first', 'error'); return; }
  await submitAttendance(token);
  document.getElementById('manual-token').value = '';
}

// ── Submit Attendance ─────────────────────────────────────────────

async function submitAttendance(payload) {
  const resultDiv = document.getElementById('scan-result');
  resultDiv.classList.remove('hidden');
  resultDiv.innerHTML = '<div style="color:var(--text2)"><i class="fas fa-spinner fa-spin"></i> Marking attendance…</div>';

  try {
    const data = await API.markAttendance(payload);

    const isLate = data.status === 'late';
    resultDiv.innerHTML = `
      <div style="background:${isLate ? 'rgba(251,146,60,0.1)' : 'rgba(52,211,153,0.1)'};
                  border:1px solid ${isLate ? 'rgba(251,146,60,0.3)' : 'rgba(52,211,153,0.3)'};
                  border-radius:12px; padding:20px; text-align:center">
        <i class="fas fa-${isLate ? 'clock' : 'check-circle'}" style="font-size:2rem;color:${isLate ? 'var(--orange)' : 'var(--green)'};margin-bottom:8px;display:block"></i>
        <strong>${data.message}</strong><br>
        <span style="color:var(--text2);font-size:0.85rem">${data.subject} · ${data.date} ${data.time}</span>
      </div>`;

    showToast(data.message, isLate ? 'info' : 'success');
    loadRecentAttendance();
  } catch (err) {
    const msg = err.error || 'Failed to mark attendance';
    resultDiv.innerHTML = `
      <div style="background:rgba(248,113,113,0.1);border:1px solid rgba(248,113,113,0.3);
                  border-radius:12px;padding:20px;text-align:center">
        <i class="fas fa-times-circle" style="font-size:2rem;color:var(--red);margin-bottom:8px;display:block"></i>
        <strong>${msg}</strong>
      </div>`;
    showToast(msg, 'error');
  }
}

// ── Recent Attendance ─────────────────────────────────────────────

async function loadRecentAttendance() {
  try {
    const records = await API.myAttendance();
    const list    = document.getElementById('recent-attendance-list');

    if (!records.length) {
      list.innerHTML = '<div style="color:var(--text3);text-align:center;padding:20px">No attendance records yet</div>';
      return;
    }

    list.innerHTML = records.slice(0, 8).map(r => `
      <div class="recent-item">
        <div class="recent-item-icon ${r.status}">
          <i class="fas fa-${r.status === 'present' ? 'check' : 'clock'}"></i>
        </div>
        <div class="recent-item-info">
          <div class="recent-item-sub">${r.subject}</div>
          <div class="recent-item-meta">${formatDate(r.session_date)} · ${r.status}</div>
        </div>
      </div>
    `).join('');
  } catch {}
}

// ── My Attendance Table ───────────────────────────────────────────

async function loadMyAttendance() {
  const subject = document.getElementById('s-subject-filter')?.value || '';
  try {
    const records = await API.myAttendance(subject);
    const tbody   = document.getElementById('s-attendance-tbody');

    tbody.innerHTML = records.map(r => `
      <tr>
        <td><strong>${r.subject}</strong></td>
        <td>${formatDate(r.session_date)}</td>
        <td>${r.time}</td>
        <td>${r.teacher_name}</td>
        <td>${statusBadge(r.status)}</td>
      </tr>
    `).join('') || '<tr><td colspan="5" style="text-align:center;color:var(--text3);padding:32px">No records found</td></tr>';

    loadSubjects();
  } catch {}
}

// ── My Stats ──────────────────────────────────────────────────────

async function loadMyStats() {
  try {
    const data     = await API.myStats();
    const subjects = data.subject_stats || [];
    const trend    = data.trend         || [];

    // Subject cards
    const cardsEl = document.getElementById('s-subject-cards');
    cardsEl.innerHTML = subjects.map(s => {
      const pct = s.pct || 0;
      const cls = pct >= 75 ? 'safe' : pct >= 60 ? 'warn' : 'danger';
      return `
        <div class="subject-card">
          <div class="subject-card-name">${s.subject}</div>
          <div class="subject-pct-big ${cls}">${pct}%</div>
          <div class="subject-meta">${s.attended} / ${s.total} sessions attended</div>
          ${pct < 75 ? `<div style="color:var(--orange);font-size:0.78rem;margin-top:6px">
            <i class="fas fa-exclamation-triangle"></i> ${sessionsNeeded(s.attended, s.total)} more to reach 75%
          </div>` : ''}
        </div>`;
    }).join('') || '<div style="color:var(--text3)">No data available</div>';

    // Trend chart
    renderStudentTrend(trend);

    // Subject donut
    renderStudentSubjectChart(subjects);
  } catch (err) {
    console.error('Stats error', err);
  }
}

function sessionsNeeded(attended, total, threshold = 75) {
  let a = attended, t = total, n = 0;
  while ((a / Math.max(t, 1)) * 100 < threshold && n < 200) { a++; t++; n++; }
  return n;
}

function renderStudentTrend(trend) {
  const ctx = document.getElementById('chart-s-trend').getContext('2d');
  if (sTrendChart) sTrendChart.destroy();

  sTrendChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: trend.map(t => formatDate(t.date)),
      datasets: [{
        label: 'Sessions Attended',
        data:  trend.map(t => t.count),
        backgroundColor: 'rgba(79,142,247,0.7)',
        borderRadius: 6,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: '#9095b8' }, grid: { color: 'rgba(255,255,255,0.04)' } },
        y: { ticks: { color: '#9095b8', precision: 0 }, grid: { color: 'rgba(255,255,255,0.04)' }, beginAtZero: true }
      }
    }
  });
}

function renderStudentSubjectChart(subjects) {
  const ctx = document.getElementById('chart-s-subjects').getContext('2d');
  if (sSubjectChart) sSubjectChart.destroy();

  const COLORS = ['#4f8ef7','#34d399','#fb923c','#a78bfa','#fbbf24','#f87171'];

  sSubjectChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: subjects.map(s => s.subject),
      datasets: [{
        data: subjects.map(s => s.pct || 0),
        backgroundColor: COLORS,
        borderWidth: 2, borderColor: '#131626',
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

function toggleStudentSidebar() {
  document.getElementById('student-sidebar').classList.toggle('open');
}

// ── Shared helpers (duplicated from teacher.js for independence) ──

function statusBadge(status) {
  const map = { present: 'badge-green', late: 'badge-orange', absent: 'badge-red' };
  return `<span class="badge ${map[status]||'badge-blue'}">${status}</span>`;
}

function formatDate(d) {
  if (!d) return '—';
  return new Date(d + 'T00:00:00').toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric'
  });
}
