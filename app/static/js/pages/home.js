/* ============================================================
   HOME — cinematic dashboard
   Hero + data-driven countdown, today's games, featured player,
   standings preview, upcoming events.
   ============================================================ */
(function () {
  "use strict";
  const HI_ = window.HI.escape;
  const L = window.HI.fmtNum;

  function gameRow(g) {
    const live = g.state === "LIVE" || g.state === "CRIT";
    const final = g.state === "FINAL" || g.state === "OFF";
    const awayWin = final && g.away.score > g.home.score;
    const homeWin = final && g.home.score > g.away.score;
    const stateLabel = live
      ? '<span class="live"><span class="live-dot"></span>' + (g.clock ? g.clock : "P" + (g.period || "?")) + "</span>"
      : final ? "Final" : (g.eastern_time || "TBA");
    const row = (team, win) =>
      '<div class="teamline' + (final && win ? " winner" : "") + '"><span class="logo"><img alt="" loading="lazy" src="' + L_URL(team.logo) + '"></span>' +
      '<span class="tname">' + HI_(team.name) + "</span>" +
      '<span class="score">' + (final || live ? L(team.score) : "") + "</span></div>";
    return (
      '<div class="game-card">' +
      '<div class="gstate"><span>' + HI_(g.season_label || "") + "</span><span>" + stateLabel + "</span></div>" +
      row(g.away, awayWin) + row(g.home, homeWin) +
      "</div>"
    );
  }

  function L_URL(u) { return u ? u : "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3C/svg%3E"; }

  async function home(ctx) {
    try {
      const [facts, sched, ev, top, st] = await Promise.all([
        window.HI.api("/api/season-facts"),
        window.HI.api("/api/schedule?date=today"),
        window.HI.api("/api/events"),
        window.HI.api("/api/stats/leaders/career?metric=points&stat_type=skater&limit=1"),
        window.HI.api("/api/standings?season_id=20242025&game_type=2"),
      ]);
      const targetMs = window.HI.epochMs(facts.regular_season.start);
      const feat = (top && (top.rows || top.results) && (top.rows || top.results)[0]) || null;
      const featured = feat
        ? await window.HI.api("/api/players/" + feat.player_id).catch(() => feat)
        : null;

      const games = sched.games || [];
      const anyLive = games.some((g) => g.state === "LIVE" || g.state === "CRIT");
      const gamesBlock = games.length
        ? '<div class="grid" style="grid-template-columns:repeat(auto-fill,minmax(300px,1fr));">' +
          games.map(gameRow).join("") + "</div>"
        : '<div class="empty"><div class="glyph">🥅</div><h4>No games today</h4>' +
          "<p>The league is between dates. Next league date: " +
          HI_(sched.next_start_date || "TBA") +
          " — the countdown below will flip to live hockey soon.</p></div>";

      const eventsUp = (ev.events || [])
        .filter((e) => !e.is_past && e.countdown_seconds != null)
        .slice(0, 4);

      const html =
        '<!-- HERO -->' +
        '<section class="hero">' +
        '<div class="krill"></div>' +
        '<div class="inner">' +
        '<div><span class="eyebrow">' + HI_(facts.regular_season.start || "") + " · 2026-27 NHL Season</span></div>" +
        "<h1>The puck drops in</h1>" +
        window.HI.countdownHtml("hero") +
        '<p class="sub">A cinematic, data-driven universe across players, teams, franchises and history — with a local AI analyst that reasons over the numbers.</p>' +
        '<div class="row wrap">' +
        '<a class="btn accent" href="#/schedule">Upcoming schedule</a>' +
        '<a class="btn" href="#/ai">Ask the AI analyst</a>' +
        '<a class="btn ghost" href="#/standings">Full standings</a>' +
        "</div>" +
        '<div class="row wrap" style="gap:10px;margin-top:6px;">' +
        '<span class="pill-tag cyan">' + L(facts.league.teams) + " teams</span>" +
        '<span class="pill-tag gold">' + L(facts.league.regular_season_games) + " regular-season games</span>" +
        '<span class="pill-tag">' + L(facts.league.seasons_tracked) + " seasons tracked</span>" +
        "</div>" +
        "</div>" +
        "</section>" +

        '<div class="section">' +
        '<div class="head"><div><span class="eyebrow">' + (anyLive ? "LIVE NOW" : "Scoreboard") + "</span>" +
        '<h2>' + (anyLive ? "Live across the league" : "Today & upcoming") + "</h2></div>" +
        '<a class="btn ghost sm" href="#/schedule">Full schedule →</a></div>' +
        gamesBlock +
        "</div>" +

        '<div class="section">' +
        '<div class="head"><div><span class="eyebrow">Spotlight</span><h2>Featured player</h2></div>' +
        '<a class="btn ghost sm" href="#/players">All players →</a></div>' +
        (featured
          ? featuredCard(featured, feat.value)
          : '<div class="empty"><h4>No featured player</h4></div>') +
        "</div>" +

        '<div class="grid" style="grid-template-columns:1.4fr 1fr;">' +
        '<div class="card">' +
        '<div class="head"><h3>2024-25 League standings</h3>' +
        '<a class="btn ghost sm" href="#/standings">Full table →</a></div>' +
        standingsMini((st.rows || []).slice(0, 8), st.season_label) +
        "</div>" +
        '<div class="card">' +
        '<div class="head"><h3>Upcoming events</h3>' +
        '<a class="btn ghost sm" href="#/events">All events →</a></div>' +
        eventsMini(eventsUp) +
        "<p class='panel-tip' style='margin-top:14px;'>Dates come from the NHL schedule API and configured league calendar — nothing is hard-coded in the UI.</p>" +
        "</div>" +
        "</div>";

      return {
        html,
        bind(view) {
          window.HI.bindCountdown(view, targetMs);
        },
      };
    } catch (err) {
      return "<div class='error-block'>" + HI_(err && err.message) + "</div>";
    }
  }

  function featuredCard(p, value) {
    const hero = p.hero
      ? "<img src='" + HI_(p.hero) + "' alt='" + HI_(p.full_name) + "' style='width:100%;height:100%;object-fit:cover;'>"
      : '<span class="fallback">' + HI_(window.HI.initials(p.full_name)) + "</span>";
    const headshot = p.headshot
      ? "<img src='" + HI_(p.headshot) + "' alt='' style='width:64px;height:64px;border-radius:16px;object-fit:cover;border:1px solid var(--line);'>"
      : "";
    return (
      '<div class="card hover" style="display:flex;gap:20px;align-items:center;overflow:hidden;">' +
      '<div style="flex:none;width:clamp(120px,22vw,220px);aspect-ratio:4/5;border-radius:14px;overflow:hidden;border:1px solid var(--line-strong);background:radial-gradient(circle at 30% 16%,#16304a,#070b14);display:grid;place-items:center;">' +
      hero + "</div>" +
      '<div class="grow">' +
      '<div class="row"><span class="eyebrow">All-time points leader</span></div>' +
      '<h2 style="font-size:clamp(20px,2.6vw,30px);margin:6px 0 2px;">' + HI_(p.full_name) + "</h2>" +
      '<div class="muted" style="font-size:13px;">' +
      HI_(p.position || "") + (p.team_abbreviation ? " · " + HI_(p.team_abbreviation) : "") +
      " · Career points <b style='color:var(--cyan);'>" + L(value) + "</b></div>" +
      '<div class="row wrap" style="margin-top:16px;">' +
      '<a class="btn sm accent" href="#/players/' + p.player_id + '">Open profile</a>' +
      window.HI.favBtn({ type: "player", id: p.player_id, name: p.full_name, sub: p.team_abbreviation || "Player" }) +
      "</div>" +
      "</div>" +
      '<div style="align-self:flex-end;">' + headshot + "</div>" +
      "</div>"
    );
  }

  function standingsMini(rows, label) {
    return (
      '<table class="dtable"><thead><tr>' +
      '<th>#</th><th>Team</th><th class="num">GP</th><th class="num">W</th>' +
      '<th class="num">L</th><th class="num">OT</th><th class="num">PTS</th></tr></thead><tbody>' +
      rows.map((r) =>
        '<tr class="' + (r.in_playoffs ? "playoff" : "") + '">' +
        '<td><span class="rank">' + r.rank + "</span></td>" +
        '<td><span class="teamcell"><img alt="" loading="lazy" src="' + L_URL(r.logo) + '">' + HI_(r.abbreviation) + "</span></td>" +
        '<td class="num">' + L(r.games_played) + "</td>" +
        '<td class="num">' + L(r.wins) + "</td>" +
        '<td class="num">' + L(r.losses) + "</td>" +
        '<td class="num">' + L(r.ot_losses || 0) + "</td>" +
        '<td class="num" style="color:var(--cyan);font-weight:700;">' + L(r.points) + "</td>" +
        "</tr>"
      ).join("") +
      '</tbody></table>' +
      '<p class="panel-tip" style="margin-top:12px;">' + (label || "2024-25") + " · league-wide, sorted by points. Bubble = playoff position.</p>"
    );
  }

  function eventsMini(events) {
    if (!events.length) return '<div class="empty"><h4>Nothing scheduled yet</h4></div>';
    return (
      '<div class="timeline" style="margin-top:4px;">' +
      events.map((e) =>
        '<div class="tl-item">' +
        '<div class="tl-date">' + HI_(e.date || "TBA") + "</div>" +
        "<h4>" + HI_(e.title) + "</h4>" +
        "<p>" + window.HI.fmtNum(e.countdown_seconds / 86400 > 1 ? Math.round(e.countdown_seconds / 86400) + " days away" : Math.round(e.countdown_seconds / 3600) + " hours away") + "</p>" +
        "</div>"
      ).join("") +
      "</div>"
    );
  }

  async function live(ctx) {
    try {
      const sched = await window.HI.api("/api/schedule?date=today");
      const games = (sched.games || []).filter((g) => g.state === "LIVE" || g.state === "CRIT");
      const html =
        '<h1 class="page-title">Live NHL</h1>' +
        '<p class="page-sub">Every game currently in progress, pulled live from the league schedule endpoint.</p>' +
        (games.length
          ? '<div class="grid">' + games.map(gameRow).join("") + "</div>"
          : '<div class="empty"><div class="glyph">📡</div><h4>No games live right now</h4>' +
            "<p>When the league is dark, this board rests. Check the schedule page for the next slate.</p></div>");
      return { html };
    } catch (err) {
      return "<div class='error-block'>" + HI_(err && err.message) + "</div>";
    }
  }

  window.HI_Home = home;
  window.HI_Live = live;
})();