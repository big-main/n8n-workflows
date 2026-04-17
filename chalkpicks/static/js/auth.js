const Auth = {
  getToken()   { return localStorage.getItem('cp_access'); },
  getRefresh() { return localStorage.getItem('cp_refresh'); },
  getUser()    { try { return JSON.parse(localStorage.getItem('cp_user') || 'null'); } catch { return null; } },

  save(data) {
    localStorage.setItem('cp_access',  data.access_token);
    localStorage.setItem('cp_refresh', data.refresh_token);
    localStorage.setItem('cp_user',    JSON.stringify(data.user));
  },

  clear() {
    ['cp_access','cp_refresh','cp_user'].forEach(k => localStorage.removeItem(k));
  },

  isLoggedIn() { return !!this.getToken(); },

  async login(email, password) {
    const res  = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Login failed');
    this.save(data);
    return data;
  },

  async register(email, username, password) {
    const res  = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, username, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Registration failed');
    this.save(data);
    return data;
  },

  async tryRefresh() {
    const rt = this.getRefresh();
    if (!rt) return false;
    try {
      const res  = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: rt }),
      });
      if (!res.ok) { this.clear(); return false; }
      const data = await res.json();
      localStorage.setItem('cp_access', data.access_token);
      return true;
    } catch { return false; }
  },

  async logout() {
    const rt = this.getRefresh();
    if (rt) {
      fetch('/api/auth/logout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: rt }),
      }).catch(() => {});
    }
    this.clear();
    window.location = '/login';
  },

  // Redirect to /login if not authenticated (call on protected pages)
  requireAuth() {
    if (!this.isLoggedIn()) { window.location = '/login'; return false; }
    return true;
  },

  // Redirect to /app if already logged in (call on login page)
  redirectIfAuthed() {
    if (this.isLoggedIn()) { window.location = '/app'; }
  },
};
