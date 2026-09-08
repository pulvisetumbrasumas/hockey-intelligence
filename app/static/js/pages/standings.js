/* ============================================================
   STANDINGS — full league table + leaderboards
   ============================================================ */
(function () {
  "use strict";
  const HI_ = window.HI.escape;
  const L = window.HI.fmtNum;

  const SEASONS = [
    20242025, 20232024, 20222023, 20212022, 20202021,
    20192020, 20182019, 20172018, 20162017, 20152016,
  ];

  const METRICS = [
    ["points", "Points", "skater"],
    ["goals", "Goals", "skater"],
    ["assists", "Assists", "skater"],
    ["plus_minus", "Plus/Minus", "skater"],
    ["wins", "Wins", "goalie"],
    ["save_pct", "Save %", "goalie"],
    ["goals_against_average", "GAA", "goalie"],
  ];

  async function standings(ctx) {
    try {
      const seasonId = 20242025;
      const [st, facts] = await Promise.all([
        window.HI.api("/api/standings?season_id=" + seasonId + "&game_type=2"),
        window.HI.api("/api/season-facts").catch(() => null),
      ]);
      const rows = st.rows || [];

      const html =
        '<h1 class="page-title">Standings</h1>' +
        '<p class="page-sub">League table computed from the database — points, then regulation wins and goal differential as tiebreaks. Playoff bubble = top 16.</p>' +
        '<div class="card" style="overflow-x:auto;margin-bottom:22px;">' +
        '<table class="dtable" style="min-width:760px;">' +
        "<thead><tr><th>#</th><th>Team</th><th class='num'>GP</th><th class='num'>W</th>" +
        "<th class='num'>L</th><th class='num'>OT</th><th class='num'>PTS</th>" +
        "<th class='num'>GF</th><th class='num'>GA</th><th class='num'>DIFF</th>" +
        "<th class='num'>ROW</th><th class='num'>P%</th></tr></thead><tbody>" +
        rows.map((r) =>
          '<tr class="' + (r.in_playoffs ? "playoff" : "") + '">' +
          '<td><span class="rank">' + r.rank + "</span></td>" +
          '<td><span class="teamcell"><img alt="" loading="lazy" src="' + (r.logo || "") + '">' +
          HI_(r.abbreviation || r.name) + "</span></td>" +
          '<td class="num">' + L(r.games_played) + "</td>" +
          '<td class="num">' + L(r.wins) + "</td>" +
          '<td class="num">' + L(r.losses) + "</td>" +
          '<td class="num">' + L(r.ot_losses || 0) + "</td>" +
          '<td class="num" style="font-weight:700;color:var(--cyan);">' + L(r.points) + "</td>" +
          '<td class="num">' + L(r.goals_for) + "</td>" +
          '<td class="num">' + L(r.goals_against) + "</td>" +
          '<td class="num' + (r.goal_differential > 0 ? '" style="color:#69e0a0;">+' : '" style="color:#ff8793;">') + L(r.goal_differential) + "</td>" +
          '<td class="num">' + L(r.row) + "</td>" +
          '<td class="num">' + Number(r.points_pct).toFixed(3).slice(1) + "</td>" +
          "</tr>"
        ).join("") +
        "</tbody></table>" +
        '<p class="panel-tip" style="margin-top:12px;">' + HI_(st.season_label || "2024-25") + " regular season · " +
        HI_(st.note || "") + "</p></div>" +

        '<div class="section"><div class="head">' +
        '<div><span class="eyebrow">Deterministic engine</span><h2>League leaders</h2></div>' +
        "</div></div>" +
        leadersBlock() +

        '<p class="panel-tip" style="margin-top:18px;">' +
        "Leaderboard pools every player with regular-season games in the ten seeded seasons (2015-16 → 2024-25). Career = summed across those seasons.</p>";

      return {
        html,
        async bind(view) {
          const container = view.querySelector("#leaders-block");
          const tabs = container.querySelectorAll(".tab[data-metric]");
          const sel = container.querySelector("#leaders-scope");
          const apply = async () => {
            const metric = container.querySelector(".tab.active").dataset.metric;
            const statType = container.querySelector(".tab.active").dataset.type;
            const scope = sel.value;
            const data = await window.HI.api(
              "/api/stats/leaders/" + (scope === "season" ? "season/20242025" : "career") +
              "?metric=" + encodeURIComponent(metric) + "&stat_type=" + statType + "&limit=10"
            );
            const rows = data.results || data.rows || [];
            container.querySelector("#leaders-rows").innerHTML =
              rows.map((r, i) =>
                '<a href="#/players/' + r.player_id + '" class="row" style="padding:8px 10px;border-radius:10px;">' +
                '<span class="rank" style="width:24px;height:24px;border-radius:7px;display:grid;place-items:center;font-size:11px;font-weight:700;background:rgba(255,255,255,.05);color:var(--text-3);">' + (i + 1) + "</span>" +
                '<span class="grow" style="font-weight:600;">' + HI_(r.name || r.full_name) + "</span>" +
                '<span class="muted" style="font-size:12px;">' + HI_(r.team || "") + "</span>" +
                '<span class="num" style="font-weight:700;color:var(--cyan);">' + fmtL(r.value, statType) + "</span>" +
                "</a>"
              ).join("") || '<div class="empty" style="padding:14px;"><h4>No data</h4></div>';
          };
          tabs.forEach((t) =>
            t.addEventListener("click", () => {
              tabs.forEach((x) => x.classList.remove("active"));
              t.classList.add("active");
              apply();
            })
          );
          sel.addEventListener("change", apply);
          apply();
        },
      };
    } catch (err) {
      return "<div class='error-block'>" + HI_(err && err.message) + "</div>";
    }
  }

  function fmtL(v, statType) {
    if (v == null) return "—";
    if ((statType === "goalie") && typeof v === "number" && !Number.isInteger(v)) return v.toFixed(3);
    return L(v);
  }

  function leadersBlock() {
    return (
      '<div class="card" id="leaders-block">' +
      '<div class="row wrap" style="justify-content:space-between;gap:12px;">' +
      '<div class="tabs" style="margin:0;">' +
      METRICS.map(([m, label, ty], i) =>
        '<button class="tab' + (i === 0 ? " active" : "") + '" data-metric="' + m + '" data-type="' + ty + '">' + HI_(label) + "</button>"
      ).join("") +
      "</div>" +
      '<select class="field" id="leaders-scope" style="height:36px;">' +
      '<option value="career">Career (seeded seasons)</option>' +
      '<option value="season">2024-25 season</option>' +
      "</select></div>" +
      '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:8px;margin-top:10px;" id="leaders-rows">' +
      '<div class="loading-block"><div class="spinner" style="margin:10px auto;"></div></div>' +
      "</div></div>"
    );
  }

  window.HI_Standings = standings;
})();