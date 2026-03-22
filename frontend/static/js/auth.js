/**
 * auth.js — Login, registration, session management
 */

let currentRole = 'teacher';   // 'teacher' | 'student'
let currentUser = null;

// ── Page entry ────────────────────────────────────────────────────

function enterAsTeacher() {
  currentRole = 'teacher';
  document.getElementById('auth-title').textContent    = 'Teacher Login';
  document.getElementById('auth-subtitle').textContent = 'Access your dashboard';
  document.getElementById('auth-icon').className       = 'fas fa-chalkboard-teacher art-center-icon';
  document.getElementById('login-teacher-fields').style.display = '';
  document.getElementById('login-student-fields').style.display = 'none';
  document.getElementById('reg-student-extra').style.display    = 'none';
  switchAuthTab('login');
  showPage('auth');
}

function enterAsStudent() {
  currentRole = 'student';
  document.getElementById('auth-title').textContent    = 'Student Login';
  document.getElementById('auth-subtitle').textContent = 'Track your attendance';
  document.getElementById('auth-icon').className       = 'fas fa-user-graduate art-center-icon';
  document.getElementById('login-teacher-fields').style.display = 'none';
  document.getElementById('login-student-fields').style.display = '';
  document.getElementById('reg-student-extra').style.display    = '';
  switchAuthTab('login');
  showPage('auth');
}

function switchAuthTab(tab) {
  document.getElementById('form-login').classList.toggle('active',    tab === 'login');
  document.getElementById('form-register').classList.toggle('active', tab === 'register');
  document.getElementById('tab-login').classList.toggle('active',    tab === 'login');
  document.getElementById('tab-register').classList.toggle('active', tab === 'register');
  clearAuthErrors();
}

function clearAuthErrors() {
  document.getElementById('auth-error').classList.add('hidden');
  document.getElementById('auth-reg-error').classList.add('hidden');
}

// ── Login ─────────────────────────────────────────────────────────

async function handleLogin(e) {
  e.preventDefault();
  clearAuthErrors();

  try {
    let data;
    if (currentRole === 'teacher') {
      const email    = document.getElementById('login-email').value;
      const password = document.getElementById('login-password').value;
      data = await API.teacherLogin({ email, password });
    } else {
      const usn_or_email = document.getElementById('login-usn').value;
      const password     = document.getElementById('login-password').value;
      data = await API.studentLogin({ usn_or_email, password });
    }

    currentUser = data.user;
    onLoginSuccess(data.user);
  } catch (err) {
    showAuthError('auth-error', err.error || 'Login failed');
  }
}

function onLoginSuccess(user) {
  showToast(`Welcome, ${user.name}!`, 'success');
  if (user.role === 'teacher') {
    document.getElementById('t-name').textContent   = user.name;
    document.getElementById('t-avatar').textContent = user.name[0].toUpperCase();
    showPage('teacher');
    teacherTab('overview');
    loadDashboard();
    loadSubjects();
  } else {
    document.getElementById('s-name').textContent   = user.name;
    document.getElementById('s-usn').textContent    = user.usn || '';
    document.getElementById('s-avatar').textContent = user.name[0].toUpperCase();
    showPage('student');
    studentTab('scan');
    loadRecentAttendance();
  }
}

// ── Register ─────────────────────────────────────────────────────

async function handleRegister(e) {
  e.preventDefault();
  clearAuthErrors();

  try {
    const name     = document.getElementById('reg-name').value;
    const email    = document.getElementById('reg-email').value;
    const password = document.getElementById('reg-password').value;

    if (currentRole === 'teacher') {
      await API.teacherRegister({ name, email, password });
    } else {
      const usn = document.getElementById('reg-usn').value;
      await API.studentRegister({ name, usn, email, password });
    }

    showToast('Account created! Please log in.', 'success');
    switchAuthTab('login');
  } catch (err) {
    showAuthError('auth-reg-error', err.error || 'Registration failed');
  }
}

function showAuthError(id, msg) {
  const el = document.getElementById(id);
  el.textContent = msg;
  el.classList.remove('hidden');
}

// ── Logout ────────────────────────────────────────────────────────

async function logout() {
  await API.logout().catch(() => {});
  currentUser = null;
  showPage('landing');
  showToast('Logged out successfully', 'info');
}

// ── Password toggle ───────────────────────────────────────────────

function togglePw(inputId) {
  const input = document.getElementById(inputId);
  input.type = input.type === 'password' ? 'text' : 'password';
}

// ── Auto-restore session ──────────────────────────────────────────

async function restoreSession() {
  try {
    const user = await API.me();
    currentUser = user;
    onLoginSuccess(user);
  } catch {
    // Not logged in — stay on landing
  }
}
