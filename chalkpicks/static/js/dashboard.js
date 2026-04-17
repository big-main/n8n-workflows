/* ── Dashboard controller ─────────────────────────────────────
   Runs on /app — requires auth.js, utils.js, picks.js loaded first
─────────────────────────────────────────────────────────────── */
const Dashboard = (() => {
  let currentSport  = '';
  let currentView   = 'picks';
  let allPicks      = [];
  let allGames      = [];
  let refreshTimer  = null;

  // ── Init ────────────────────────────────────────────────────
  async function init() {
    if (!Auth.requireAuth()) return;

    const user = Auth.getUser();
    applyUserUI(user);
    await Promise.all([loadStats(), loadSports(), loadData()]);

    // Wire up sport pills (delegated)
    document.getElementById('sportPills').addEventListener('click', e => {
      const pill = e.target.closest('.sport-pill');
      if (!pill) return;
      setSport(pill.dataset.sport);
    });

    // Wire up sidebar/mobile nav view links
    document.querySelectorAll('[data-view]').forEach(el => {
      el.addEventListener('click', e => {
        e.preventDefault();
        setView(el.dataset.view);
      });
    });

    // Billing link
    const billingLink = document.getElementById('billingLink');
    if (billingLink) {
      billingLink.addEventListener('click', async e => {
        e.preventDefault();
        if (user?.tier === 'free') { window.location = '/pricing'; return; }
        try {
          const res  = await apiFetch('/api/stripe/portal');
          const data = await res.json();
          if (data.portal_url) window.location = data.portal_url;
        } catch { Toast.show('Billing portal unavailable.', 'error'); }
      });
    }

    // Auto-refresh every 5 minutes
    refreshTimer = setInterval(() => loadData(false), 5 * 60 * 1000);

    // Flash subscription success
    if (new URLSearchParams(location.search).get('subscribed')) {
      Toast.show('🎉 Subscription activated! Welcome to the sharp side.', 'success', 5000);
      history.replaceState({}, '', '/app');
    }
  }

  // ── User UI ─────────────────────────────────────────────────
  function applyUserUI(user) {
    if (!user) return;
    const tier = user.tier || 'free';

    document.getElementById('navUsername').textContent  = user.username || '';
    document.getElementById('sidebarUsername').textContent = user.username || '';

    ['tierBadge','sidebarTier'].forEach(id => {
      const el = document.getElementById(id);
      if (!el) return;
      el.textContent  = tier.toUpperCase();
      el.className    = `tier-badge tier-${tier}`;
    });

    // Hide upgrade CTA for paid users
    const upgradeBanner = document.getElementById('upgradeBanner');
    const upgradeNavBtn = document.getElementById('upgradeNavBtn');
    if (tier !== 'free') {
      if (upgradeBanner) upgradeBanner.style.display = 'none';
      if (upgradeNavBtn) upgradeNavBtn.style.display = 'none';
    }
  }

  // ── Stats ───────────────────────────────────────────────────
  async function loadStats() {
    try {
      const res  = await fetch('/api/stats');
      const data = await res.json();
      document.getElementById('sStat1').textContent = data.total_picks  ?? '—';
      document.getElementById('sStat2').textContent = data.best_bets    ?? '—';
      document.getElementById('sStat3').textContent = (data.win_rate ?? '—') + (data.win_rate ? '%' : '');
      document.getElementById('sStat4').textContent = (data.roi != null ? '+' : '') + (data.roi ?? '—') + (data.roi != null ? '%' : '');
    } catch {}
  }

  // ── Sports pills ────────────────────────────────────────────
  async function loadSports() {
    try {
      const res    = await fetch('/api/sports');
      const data   = await res.json();
      const active = (data.sports || []).filter(s => s.active);
      const pills  = document.getElementById('sportPills');
      pills.innerHTML = `<button class="sport-pill active" data-sport="">
        <span class="emoji">🏆</span> All Sports
      </button>`;
      active.forEach(s => {
        const btn = document.createElement('button');
        btn.className    = 'sport-pill';
        btn.dataset.sport = s.key;
        btn.innerHTML    = `<span class="emoji">${s.icon}</span> ${s.name}`;
        pills.appendChild(btn);
      });
    } catch {}
  }

  // ── Load picks / games ───────────────────────────────────────
  async function loadData(showSkeleton = true) {
    const grid = document.getElementById('picksGrid');
    if (showSkeleton) renderSkeletons(grid, 6);

    try {
      const params  = currentSport ? `?sport=${currentSport}` : '';
      const [picksRes, gamesRes] = await Promise.all([
        apiFetch('/api/picks' + params + (currentSport ? '&limit=40' : '?limit=40')),
        apiFetch('/api/games' + params),
      ]);
      allPicks = (await picksRes.json()).picks || [];
      allGames = (await gamesRes.json()).games || [];
      renderView();
      const lu = document.getElementById('lastUpdated');
      if (lu) lu.textContent = 'Updated ' + Fmt.relativeTime(new Date().toISOString());
    } catch (err) {
      grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:40px; color:var(--text-muted);">
        Failed to load picks. <button class="btn btn-secondary btn-sm" onclick="Dashboard.refresh()">Retry</button>
      </div>`;
    }
  }

  // ── Render ───────────────────────────────────────────────────
  function renderView() {
    const grid  = document.getElementById('picksGrid');
    const empty = document.getElementById('emptyState');
    const title = document.getElementById('viewTitle');
    grid.innerHTML = '';

    let items;
    if (currentView === 'bestbets') {
      title.textContent = '⚡ Best Bets';
      items = allPicks.filter(p => p.is_best_bet);
    } else if (currentView === 'games') {
      title.textContent = '📅 All Games';
      renderGames(grid, allGames);
      if (empty) empty.classList.add('hidden');
      return;
    } else {
      title.textContent = "Today's Picks";
      items = allPicks;
    }

    if (!items.length) {
      if (empty) empty.classList.remove('hidden');
      return;
    }
    if (empty) empty.classList.add('hidden');
    items.forEach(p => grid.appendChild(buildPickCard(p)));
  }

  function renderGames(grid, games) {
    if (!games.length) {
      grid.innerHTML = `<div style="grid-column:1/-1;text-align:center;padding:40px;color:var(--text-muted);">No upcoming games found.</div>`;
      return;
    }
    // Group by sport
    const grouped = games.reduce((acc, g) => {
      (acc[g.league] = acc[g.league] || []).push(g);
      return acc;
    }, {});

    Object.entries(grouped).forEach(([league, gs]) => {
      const header = document.createElement('div');
      header.style.cssText = 'grid-column:1/-1; font-family:var(--font-head); font-size:0.85rem; font-weight:700; color:var(--text-muted); text-transform:uppercase; letter-spacing:.08em; margin-bottom:-8px; padding:4px 0;';
      header.textContent = league;
      grid.appendChild(header);
      gs.forEach(g => grid.appendChild(buildGameRow(g)));
    });
  }

  function buildGameRow(game) {
    const el = document.createElement('div');
    el.className = 'card';
    el.style.padding = '16px 20px';
    el.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">
        <div>
          <div style="font-family:var(--font-head);font-size:0.95rem;font-weight:700;">${game.away_team} @ ${game.home_team}</div>
          <div style="font-size:0.75rem;color:var(--text-muted);margin-top:3px;">${Fmt.gameTime(game.game_time)}</div>
        </div>
        <div style="display:flex;gap:16px;">
          <div style="text-align:center;">
            <div style="font-family:var(--font-head);font-weight:700;">${game.home_spread != null ? Fmt.spread(game.home_spread) : '—'}</div>
            <div style="font-size:0.68rem;color:var(--text-dim);">Spread</div>
          </div>
          <div style="text-align:center;">
            <div style="font-family:var(--font-head);font-weight:700;">${game.total ?? '—'}</div>
            <div style="font-size:0.68rem;color:var(--text-dim);">Total</div>
          </div>
          <div style="text-align:center;">
            <div style="font-family:var(--font-head);font-weight:700;">${game.home_moneyline != null ? Fmt.odds(game.home_moneyline) : '—'}</div>
            <div style="font-size:0.68rem;color:var(--text-dim);">Home ML</div>
          </div>
        </div>
      </div>`;
    return el;
  }

  // ── Public API ───────────────────────────────────────────────
  function setSport(sport) {
    currentSport = sport;
    document.querySelectorAll('.sport-pill').forEach(p => {
      p.classList.toggle('active', p.dataset.sport === sport);
    });
    loadData();
  }

  function setView(view) {
    currentView = view;
    document.querySelectorAll('[data-view]').forEach(el => {
      el.classList.toggle('active', el.dataset.view === view);
    });
    renderView();
  }

  async function refresh() {
    const btn = document.getElementById('refreshBtn');
    if (btn) btn.classList.add('loading');
    await loadData();
    await loadStats();
    if (btn) btn.classList.remove('loading');
    Toast.show('Picks refreshed', 'success', 2000);
  }

  // Auto-init
  document.addEventListener('DOMContentLoaded', init);

  return { setSport, setView, refresh };
})();
