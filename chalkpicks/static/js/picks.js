/* ── Pick card builder ───────────────────────────────────────── */
function buildPickCard(pick) {
  const el = document.createElement('div');
  el.className = `pick-card${pick.is_best_bet ? ' best-bet' : ''}${pick.is_locked ? ' locked' : ''}`;

  const typeLabel = { spread: 'Spread', moneyline: 'ML', total_over: 'Over', total_under: 'Under' }[pick.pick_type] || pick.pick_type;
  const typeClass = pick.pick_type.replace('_', '');

  const pickLabel = pick.is_locked
    ? '<span style="filter:blur(5px);user-select:none;color:var(--text-dim);">??? +0 (-110)</span>'
    : formatPickLabel(pick);

  const scoreColor = pick.chalk_score >= 85 ? '#ffd700'
                   : pick.chalk_score >= 72 ? '#00ff87'
                   : pick.chalk_score >= 58 ? '#00b4ff'
                   : '#555577';

  const tierLabel  = { pro: 'Pro', sharp: 'Sharp' }[pick.required_tier];
  const lockContent = pick.is_locked ? `
    <div class="lock-overlay">
      <span class="lock-msg">🔒 Requires <span class="lock-tier">${tierLabel}</span> plan</span>
      <a href="/pricing" class="btn btn-secondary btn-sm">Unlock</a>
    </div>` : '';

  const analysisHtml = (!pick.is_locked && pick.analysis)
    ? `<div class="pick-analysis">${pick.analysis}</div>` : '';

  const componentsHtml = (!pick.is_locked && pick.components)
    ? `<div style="padding:0 20px 4px;">
        <div style="font-size:0.68rem;color:var(--text-dim);text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px;">Score Breakdown</div>
        <div class="score-components">
          ${componentRow('Line Value', pick.components.line_value)}
          ${componentRow('Form', pick.components.form)}
          ${componentRow('Sharp $', pick.components.sharp_money)}
          ${componentRow('Situation', pick.components.situational)}
          ${componentRow('H2H', pick.components.h2h)}
        </div>
      </div>` : '';

  const evHtml = pick.ev != null && !pick.is_locked
    ? `<span style="font-size:0.72rem;color:${pick.ev >= 0 ? 'var(--chalk-green)' : 'var(--chalk-red)'}; font-weight:600;">EV ${pick.ev >= 0 ? '+' : ''}${pick.ev.toFixed(1)}%</span>`
    : '';

  el.innerHTML = `
    <div class="pick-card-header">
      <span class="pick-league">${pick.league || pick.sport}</span>
      <span class="pick-time">${Fmt.gameTime(pick.game_time)}</span>
    </div>

    <div class="pick-matchup">
      <div class="team">
        <div class="team-name">${pick.away_team}</div>
        <div class="team-record">${pick.away_ml != null ? Fmt.odds(pick.away_ml) : ''}</div>
      </div>
      <div class="vs-badge">@</div>
      <div class="team" style="text-align:right;">
        <div class="team-name">${pick.home_team}</div>
        <div class="team-record">${pick.home_ml != null ? Fmt.odds(pick.home_ml) : ''}</div>
      </div>
    </div>

    <div class="pick-recommendation${pick.is_locked ? ' locked' : ''}">
      <div>
        <div style="font-size:0.68rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:4px;">The Pick</div>
        <div class="pick-team-label">${pickLabel}</div>
      </div>
      <span class="pick-type-badge badge-${typeClass}">${typeLabel}</span>
    </div>

    <div class="chalk-score-wrap">
      ${buildGaugeSVG(pick.chalk_score)}
      <div class="score-detail">
        <div class="score-label">ChalkScore™</div>
        <div class="confidence-badge conf-${(pick.confidence || 'low').toLowerCase()}" style="margin-bottom:6px;">
          ${{ ELITE: '⚡', HIGH: '🔥', MEDIUM: '✅', LOW: '💤' }[pick.confidence] || ''}
          ${pick.confidence}
        </div>
        ${evHtml}
      </div>
    </div>

    ${componentsHtml}
    ${analysisHtml}

    <div class="pick-odds-row">
      <div class="pick-odds-item">
        <span class="odds-val">${pick.home_spread != null ? Fmt.spread(pick.home_spread) : '—'}</span>
        <span class="odds-lbl">Spread</span>
      </div>
      <div class="pick-odds-item">
        <span class="odds-val">${pick.total != null ? pick.total : '—'}</span>
        <span class="odds-lbl">Total</span>
      </div>
      <div class="pick-odds-item">
        <span class="odds-val">${pick.home_ml != null ? Fmt.odds(pick.home_ml) : '—'}</span>
        <span class="odds-lbl">Home ML</span>
      </div>
      <div class="pick-odds-item">
        <span class="odds-val">${pick.away_ml != null ? Fmt.odds(pick.away_ml) : '—'}</span>
        <span class="odds-lbl">Away ML</span>
      </div>
    </div>

    ${lockContent}
  `;
  return el;
}

function formatPickLabel(pick) {
  if (!pick.pick_team) return '???';
  const team = pick.pick_team;
  if (pick.pick_type === 'spread' && pick.pick_value != null) {
    return `${team} ${pick.pick_value > 0 ? '+' : ''}${pick.pick_value} (${Fmt.odds(pick.pick_odds)})`;
  }
  if (pick.pick_type === 'moneyline') {
    return `${team} ${Fmt.odds(pick.pick_odds)}`;
  }
  if (pick.pick_type === 'total_over' || pick.pick_type === 'total_under') {
    const dir = pick.pick_type === 'total_over' ? 'Over' : 'Under';
    return `${dir} ${pick.pick_value} (${Fmt.odds(pick.pick_odds)})`;
  }
  return team;
}

/* ── Skeleton cards ──────────────────────────────────────────── */
function renderSkeletons(container, count = 6) {
  container.innerHTML = Array(count).fill(
    `<div class="card" style="height:300px;"><div class="skeleton" style="width:100%;height:100%;border-radius:var(--radius-lg);"></div></div>`
  ).join('');
}
