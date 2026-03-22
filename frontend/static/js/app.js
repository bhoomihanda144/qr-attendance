/**
 * app.js — Page routing, shared UI utilities, initialization
 */

// ── Page Router ───────────────────────────────────────────────────

function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  const el = document.getElementById(`page-${name}`);
  if (el) el.classList.add('active');
}

// ── Sidebar toggles ───────────────────────────────────────────────

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}

// ── Toast Notifications ────────────────────────────────────────────

let toastTimer = null;

function showToast(message, type = 'info') {
  const toast   = document.getElementById('toast');
  const iconEl  = document.getElementById('toast-icon');
  const msgEl   = document.getElementById('toast-msg');

  const icons = { success: 'fa-check-circle', error: 'fa-times-circle', info: 'fa-info-circle' };
  iconEl.className = `fas ${icons[type] || icons.info}`;
  msgEl.textContent = message;

  toast.className = `toast ${type}`;
  toast.classList.remove('hidden');

  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.add('hidden'), 3500);
}

// ── Modal ──────────────────────────────────────────────────────────

function openModal() {
  document.getElementById('modal-backdrop').classList.remove('hidden');
  document.getElementById('modal').classList.remove('hidden');
}

function closeModal() {
  document.getElementById('modal-backdrop').classList.add('hidden');
  document.getElementById('modal').classList.add('hidden');
}

// ── Date display ──────────────────────────────────────────────────

function updateDate() {
  const el = document.getElementById('today-date');
  if (el) {
    el.textContent = new Date().toLocaleDateString('en-IN', {
      weekday: 'short', day: 'numeric', month: 'short', year: 'numeric'
    });
  }
}

// ── Landing page bindings ─────────────────────────────────────────

document.getElementById('btn-teacher-entry').addEventListener('click', enterAsTeacher);
document.getElementById('btn-student-entry').addEventListener('click', enterAsStudent);

// ── Init ──────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
  updateDate();
  setInterval(updateDate, 60000);

  // Try to restore an existing server session
  await restoreSession();
});
