/* ── Toast notifications ─────────────────────────────────────── */
const Toast = {
  show(msg, type = 'info', duration = 3500) {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.innerHTML = `<span class="toast-icon">${icons[type] || icons.info}</span><span class="toast-msg">${msg}</span>`;
    container.appendChild(el);
    setTimeout(() => { el.style.opacity = '0'; el.style.transform = 'translateY(10px)'; el.style.transition = '0.3s'; setTimeout(() => el.remove(), 300); }, duration);
  }
};

/* ── Formatting helpers ──────────────────────────────────────── */
const Fmt = {
  odds(ml) {
    if (ml == null) return '—';
    return ml > 0 ? `+${ml}` : String(ml);
  },
  spread(val) {
    if (val == null) return '—';
    return val > 0 ? `+${val}` : String(val);
  },
  gameTime(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    const now = new Date();
    const diff = d - now;
    if (diff < 0) return 'In Progress';
    if (diff < 3600000) return `${Math.round(diff / 60000)}m`;
    if (diff < 86400000) {
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    return d.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' }) +
      ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  },
  relativeTime(iso) {
    if (!iso) return '';
    const diff = (Date.now() - new Date(iso)) / 1000;
    if (diff < 60)   return 'just now';
    if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
    if (diff < 86400)return `${Math.round(diff / 3600)}h ago`;
    return `${Math.round(diff / 86400)}d ago`;
  }
};

/* ── ChalkScore gauge SVG ────────────────────────────────────── */
function buildGaugeSVG(score, size = 72) {
  const r = (size - 12) / 2;
  const cx = size / 2, cy = size / 2;
  const circ = 2 * Math.PI * r;
  // Only draw 75% of the circle (270 degrees)
  const arc = circ * 0.75;
  const fill = arc * (score / 100);
  const offset = arc - fill;

  const color = score >= 85 ? '#ffd700'
              : score >= 72 ? '#00ff87'
              : score >= 58 ? '#00b4ff'
              : '#555577';

  return `<svg class="gauge-svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
    <circle class="gauge-track" cx="${cx}" cy="${cy}" r="${r}"
      stroke-width="6" stroke-dasharray="${arc} ${circ - arc}"
      stroke-dashoffset="${-circ * 0.125}" transform="rotate(135 ${cx} ${cy})"/>
    <circle class="gauge-fill" cx="${cx}" cy="${cy}" r="${r}"
      stroke="${color}" stroke-width="6"
      stroke-dasharray="${fill} ${circ - fill}"
      stroke-dashoffset="${-circ * 0.125 + offset}"
      transform="rotate(135 ${cx} ${cy})"/>
    <text class="gauge-text" x="${cx}" y="${cy}" fill="${color}" font-size="${size < 60 ? 11 : 14}">${score}</text>
  </svg>`;
}

/* ── Component bar row ───────────────────────────────────────── */
function componentRow(label, value) {
  if (value == null) return '';
  const pct = Math.round(value);
  const color = pct >= 70 ? 'var(--chalk-green)' : pct >= 50 ? 'var(--chalk-blue)' : 'var(--text-dim)';
  return `<div class="component-row">
    <span class="component-label">${label}</span>
    <div class="component-bar"><div class="component-fill" style="width:${pct}%;background:${color};"></div></div>
    <span class="component-val">${pct}</span>
  </div>`;
}

/* ── Generic fetch with auth ─────────────────────────────────── */
async function apiFetch(url, opts = {}) {
  const token = localStorage.getItem('cp_access');
  const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) };
  if (token) headers['Authorization'] = 'Bearer ' + token;
  const res = await fetch(url, { ...opts, headers });
  if (res.status === 401) {
    // Try refresh
    const refreshed = await Auth.tryRefresh();
    if (refreshed) {
      headers['Authorization'] = 'Bearer ' + localStorage.getItem('cp_access');
      return fetch(url, { ...opts, headers });
    }
  }
  return res;
}
