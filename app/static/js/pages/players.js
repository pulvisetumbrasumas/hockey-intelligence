/* ============================================================
   PLAYERS — the league gallery + player profile
   ============================================================ */
(function () {
  "use strict";
  const HI_ = window.HI.escape;
  const L = window.HI.fmtNum;

  const GALLERY = [
    { metric: "points", label: "Points", stat_type: "skater" },
    { metric: "goals", label: "Goals", stat_type: "skater" },
    { metric: "assists", label: "Assists", stat_type: "skater" },
    { metric: "plus_minus", label: "Plus/Minus", stat_type: "skater" },
    { metric: "categories.wins", label: "Goalie wins", stat_type: "goalie", metric2: "wins" },
    { metric: "save_pct", label: "Save percentage", stat_type: "goalie" },
  ];

  async function players(ctx) {
    if (ctx.parts[1] && /^\d+$/.test(ctx.parts[1])) {
      return playerDetail(ctx);
    }
    try {
      const grid = await Promise.all(
        GALLERY.map(async (m) => {
          const metric = m.metric2 || m.metric;
          const data = await window.HI.api(
            "/api/stats/leaders/career?metric=" + encodeURIComponent(metric) +
            "&stat_type=" + m.stat_type + "&limit=5"
          ).catch(() => null);
          return { m, rows: (data && (data.rows || data.results)) || [] };
        })
      );

      const html =
        '<h1 class="page-title">Players</h1>' +
        '<p class="page-sub">Browse the league by career leaderboards — every number is computed by the deterministic statistics engine from the embedded database.</p>' +
        '<div class="card" style="margin-bottom:22px;">' +
        '<div class="multi row wrap" style="justify-content:space-between;gap:14px;">' +
        '<input class="field" id="player-search" placeholder="Search players by name or position…" style="flex:1;min-width:240px;" />' +
        '<a class="btn accent" id="player-search-go" href="#/players">Browse</a>' +
        "</div>" +
        "<div class='search-drop hidden' style='position:static;margin-top:8px;' id='player-results'></div>" +
        '<p class="panel-tip" style="margin-top:12px;">Tip: search, then open a profile. Or use the global search bar (press /) from anywhere.</p>' +
        "</div>" +
        '<div class="grid cards-xl">' +
        grid.map(
          ({ m, rows }) =>
            '<div class="card">' +
            '<div class="head"><h3>' + HI_(m.label) + "</h3>" +
            '<span class="pill-tag">Career</span></div>' +
            leaderRows(rows, m) +
            "</div>"
        ).join("") +
        "</div>" +
        '<p class="panel-tip" style="margin-top:18px;">Career leaders pool every player who has appeared in one of the ten seeded seasons (2015-16 → 2024-25).</p>';

      return {
        html,
        bind(view) {
          const box = view.querySelector("#player-search");
          const res = view.querySelector("#player-results");
          let timer = null;
          box.addEventListener("input", () => {
            clearTimeout(timer);
            const val = box.value.trim();
            if (val.length < 2) { res.classList.add("hidden"); res.innerHTML = ""; return; }
            timer = setTimeout(async () => {
              try {
                const data = await window.HI.api("/api/search?q=" + encodeURIComponent(val) + "&limit=8");
                if (!data.players.length) {
                  res.innerHTML = '<div class="search-item"><span class="sub">No players match.</span></div>';
                } else {
                  res.innerHTML = data.players.map((p) =>
                    '<div class="search-item" onclick="location.hash=\'#/players/' + p.player_id + '\'">' +
                    '<img alt="" loading="lazy" src="' + HI_(p.headshot || "") + '" onerror="this.style.display=\'none\'">' +
                    '<span class="grow"><span class="lead">' + HI_(p.full_name) + "</span>" +
                    ' <span class="sub">' + HI_(p.position || "") + (p.team_abbreviation ? " · " + HI_(p.team_abbreviation) : "") + "</span></span></div>"
                  ).join("");
                }
                res.classList.remove("hidden");
              } catch (err) {
                res.innerHTML = "<span class='sub'>" + HI_(err && err.message) + "</span>";
                res.classList.remove("hidden");
              }
            }, 220);
          });
        },
      };
    } catch (err) {
      return "<div class='error-block'>" + HI_(err && err.message) + "</div>";
    }
  }

  function leaderRows(rows, m) {
    if (!rows.length) return '<div class="empty" style="padding:16px;"><h4>No data</h4></div>';
    const sig = m.stat_type === "goalie" ? "value" : "value";
    return (
      '<div style="display:grid;gap:6px;">' +
      rows.map((r, i) =>
        '<a href="#/players/' + r.player_id + '" class="row" style="padding:7px 10px;border-radius:10px;text-decoration:none;">' +
        '<span class="rank" style="width:22px;height:22px;border-radius:6px;display:grid;place-items:center;font-size:11px;font-weight:700;background:rgba(255,255,255,.05);color:var(--text-3);">' + (i + 1) + "</span>" +
        '<span class="grow" style="font-weight:600;color:var(--text);">' + HI_(r.name || r.full_name) + "</span>" +
        '<span class="num" style="font-weight:700;color:var(--cyan);font-variant-numeric:tabular-nums;">' + fmtLeader(r.value, m.stat_type) + "</span>" +
        "</a>"
      ).join("") +
      "</div>"
    );
  }

  function fmtLeader(v, type) {
    if (v == null) return "—";
    if (type === "goalie" && String(v).length <= 6 && v < 1) return Number(v).toFixed(3);
    return L(v);
  }

  /* ---------------- Player profile ---------------- */
  async function playerDetail(ctx) {
    const id = Number(ctx.parts[1]);
    if (!id) return "<div class='error-block'>Invalid player.</div>";
    try {
      const [p, career] = await Promise.all([
        window.HI.api("/api/players/" + id),
        window.HI.api("/api/players/" + id + "/career"),
      ]);

      const rs = (career && career.regular_season) || {};
      const isGoalie = !!(career && career.regular_season_goalie && career.regular_season_goalie.games_played);
      const goals = career && career.regular_season_goalie;
      const active = p.active;

      const heroImg = p.hero
        ? "<img src='" + HI_(p.hero) + "' alt='" + HI_(p.full_name) + "' loading='lazy'>"
        : "";
      const photo = p.headshot
        ? "<img src='" + HI_(p.headshot) + "' alt='" + HI_(p.full_name) + "' loading='lazy'>"
        : '<span class="fallback">' + HI_(window.HI.initials(p.full_name)) + "</span>";

      const tiles = [];
      if (isGoalie) {
        tiles.push(tile("GP", goals.games_played, "cyan"), tile("W", goals.wins), tile("SO", goals.shutouts, "cyan"), tile("SV%", Number(goals.save_pct).toFixed(3)));
      } else {
        tiles.push(tile("GP", rs.games_played, "cyan"), tile("Goals", rs.goals), tile("Assists", rs.assists), tile("Points", rs.points, "cyan"));
        if ((rs.plus_minus || 0) !== 0) tiles.push(tile("+/-", rs.plus_minus));
        if ((rs.shots || 0) > 0) tiles.push(tile("Shots", rs.shots));
        if ((rs.game_winning_goals || 0) > 0) tiles.push(tile("GWG", rs.game_winning_goals));
        if ((rs.power_play_goals || 0) > 0) tiles.push(tile("PPG", rs.power_play_goals));
        if ((rs.shorthanded_goals || 0) > 0) tiles.push(tile("SHG", rs.shorthanded_goals));
        if ((rs.seasons_played || 0) > 0) tiles.push(tile("Seasons", rs.seasons_played));
      }
      if ((rs.points_per_game != null) && !isGoalie) tiles.push(tile("PPG", Number(rs.points_per_game).toFixed(3)));

      const html =
        '<div class="card" style="margin-top:22px;overflow:hidden;">' +
        '<div style="height:160px;position:relative;">' +
        (heroImg
          ? heroImg + '<div style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(4,6,12,0) 20%,rgba(4,6,12,.9) 95%);"></div>'
          : '<div style="height:100%;background:radial-gradient(600px 200px at 20% 0%,rgba(53,215,255,.16),transparent 60%);"></div>') +
        "</div>" +
        '<div class="profile-hero" style="padding:0 24px;margin-top:-70px;position:relative;">' +
        '<div class="profile-photo" style="box-shadow:0 30px 80px rgba(0,0,0,.6),var(--glow-cyan);">' + photo + "</div>" +
        '<div class="profile-name">' +
        '<span class="eyebrow">' + (active ? "Active" : "Former") + " · " + HI_(p.position || "") + "</span>" +
        '<h1>' + HI_(p.full_name) + "</h1>" +
        '<span class="pos-pill">' + (isGoalie ? "Goaltender" : HI_(p.position || "Skater")) + "</span>" +
        '<div class="row wrap" style="margin-top:14px;">' +
        window.HI.favBtn({ type: "player", id: p.player_id, name: p.full_name, sub: (p.team_abbreviation || p.position || "Player") }) +
        '<a class="btn sm" href="#/compare?p=' + p.player_id + '">Compare</a>' +
        '<a class="btn sm ghost" href="#/ai?q=' + encodeURIComponent("Break down " + p.full_name + "'s game") + '">Ask AI</a>' +
        "</div>" +
        "</div>" +
        "</div>" +
        "</div>" +

        '<div class="section"><div class="head"><h2>Career totals' + (rs.seasons_played ? " · " + rs.seasons_played + " seasons" : "") + "</h2></div>" +
        '<div class="stats-hero">' + tiles.join("") + "</div></div>" +

        '<div class="section"><div class="head"><h2>Player & bio</h2></div>"' +
        '<div class="factgrid">' +
        fact("Position", p.position) +
        fact("Shoots / catches", p.shoots_catches) +
        fact("Height", p.height) +
        fact("Weight", p.weight + " lb") +
        fact("Born", p.birth_date) +
        fact("Birthplace", ((p.birth_city || "") + (p.birth_country ? ", " + p.birth_country : "")) || "—") +
        fact("Draft", p.draft_year ? (p.draft_year + " · R" + (p.draft_round || "?") + " · #" + (p.draft_overall || "?")) : "Undrafted") +
        fact("Team", p.team_abbreviation || "—") +
        fact("NHL id", p.nhl_id) +
        "</div></div>" +

        '<div class="section"><div class="head"><h2>Season by season</h2></div>' +
        await seasonTable(id) +
        "</div>" +

        '<div class="section"><div class="head"><h2>Points per season</h2></div>' +
        await seasonChart(id) +
        "</div>";

      return { html };
    } catch (err) {
      return "<div class='error-block'>" + HI_(err && err.message) + "</div>";
    }
  }

  function tile(k, v, color) {
    return (
      '<div class="stat-tile"><div class="v' + (color ? " " + color : "") + '">' +
      (v == null || isNaN(v) ? "—" : String(v)) +
      "</div><div class='k'>" + HI_(k) + "</div></div>"
    );
  }

  function fact(k, v) {
    return '<div class="fact"><div class="k">' + HI_(k) + '</div><div class="v">' + HI_(v || "—") + "</div></div>";
  }

  async function seasonTable(id) {
    let rows = [];
    try {
      const data = await window.HI.api("/api/players/" + id + "/seasons?game_type=2");
      rows = data.seasons || [];
    } catch (_) {}
    if (!rows.length) return '<div class="empty"><h4>No regular-season rows for this player</h4></div>';
    const max = Math.max.apply(null, rows.map((r) => r.points || 0)) || 1;
    return (
      '<div class="card" style="overflow-x:auto;">' +
      '<table class="dtable" style="min-width:640px;"><thead><tr>' +
      "<th>Season</th><th>Team</th><th class='num'>GP</th><th class='num'>G</th>" +
      "<th class='num'>A</th><th class='num'>PTS</th><th class='num'>+/-</th><th>PTS / season</th></tr></thead><tbody>" +
      rows.map((r) =>
        '<tr><td>' + HI_(String(r.season_id).slice(0, 4) + "-" + String(r.season_id).slice(6, 8)) + "</td>" +
        '<td>' + HI_((r.team || "").split(",")[0] || "—") + "</td>" +
        '<td class="num">' + L(r.games_played) + "</td>" +
        '<td class="num">' + L(r.goals) + "</td>" +
        '<td class="num">' + L(r.assists) + "</td>" +
        '<td class="num" style="font-weight:700;color:var(--cyan);">' + L(r.points) + "</td>" +
        '<td class="num">' + (r.plus_minus != null ? "+" + r.plus_minus : "—") + "</td>" +
        '<td style="min-width:120px;"><div class="bar"><i style="width:' + Math.round((r.points / max) * 100) + '%;"></i></div></td>' +
        "</tr>"
      ).join("") +
      "</tbody></table></div>"
    );
  }

  async function seasonChart(id) {
    let rows = [];
    try {
      const data = await window.HI.api("/api/players/" + id + "/seasons?game_type=2");
      rows = data.seasons || [];
    } catch (_) {}
    if (!rows.length) return "";
    const max = Math.max.apply(null, rows.map((r) => r.points || 0)) || 1;
    return (
      '<div class="card">' +
      '<div class="ledbar" style="flex-wrap:wrap;">' +
      rows.map((r) =>
        '<div class="seg" title="' + String(r.season_id) + " · " + L(r.points) + " pts" + '" style="display:grid;gap:6px;justify-items:center;">' +
        '<div style="height:' + Math.max(6, Math.round((r.points / max) * 90)) + "px;width:100%;max-width:22px;border-radius:5px 5px 0 0;" +
        'background:linear-gradient(180deg,#35d7ff,#7aa2ff);box-shadow:0 0 10px rgba(53,215,255,.35);"></div>' +
        '<span class="dim" style="font-size:9px;">' + HI_(String(r.season_id).slice(2, 4) + String(r.season_id).slice(6, 8)) + "</span>" +
        "</div>"
      ).join("") +
      "</div>" +
      '<p class="panel-tip" style="margin-top:14px;">Bar height = season points. Bars are pure data — heights are scaled to the player’s own best season.</p>' +
      "</div>"
    );
  }

  window.HI_Players = players;
  window.HI_PlayerDetail = playerDetail;
})();