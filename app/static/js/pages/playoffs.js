/* ============================================================
   PLAYOFFS — restored bracket history (conference finals + Cup Final)
   ============================================================ */
(function () {
  "use strict";
  const HI_ = window.HI.escape;
  const L = window.HI.fmtNum;
  const BLANK =
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3C/svg%3E";

  function teamLine(team, games, champion) {
    return (
      '<div class="teamline' + (champion ? " winner" : "") + '">' +
      '<span class="logo"><img alt="" loading="lazy" src="' +
      (team && team.logo ? team.logo : BLANK) + '"></span>' +
      '<span class="tname">' +
      (team && team.team_id
        ? '<a href="#/teams/' + team.team_id + '" style="text-decoration:none;">' + HI_(team.name) + "</a>"
        : HI_(team ? team.name : "—")) +
      "</span>" +
      '<span class="score">' + (games != null ? L(games) : "") + "</span></div>"
    );
  }

  function seriesCard(r) {
    const label =
      r.round_number === 4
        ? "Stanley Cup Final"
        : HI_(r.conference || "") + " Conference Final"; 
    const note =
      r.note ? '<div class="gstate"><span>' + HI_(r.note) + "</span></div>" : "";
    return (
      '<div class="game-card" style="min-width:280px;">' +
      '<div class="gstate"><span>' + label + "</span>" +
      (r.round_number === 4 && r.winner
        ? "<span class='pill-tag cyan' title='Series winner'>Cup</span>"
        : "") +
      "</div>" +
      teamLine(r.winner, r.winner_games, true) +
      teamLine(r.runner_up, r.runner_games, false) +
      note +
      "</div>"
    );
  }

  async function playoffs(ctx) {
    try {
      const seasonsData = await window.HI.api("/api/seasons");
      const opts = (seasonsData.seasons || [])
        .slice()
        .sort((a, b) => Number(b.season_id) - Number(a.season_id));
      const latest = opts.length ? Number(opts[0].season_id) : 20252026;
      const selId = Number((ctx.query && ctx.query.season) || latest);

      const data = await window.HI.api("/api/playoffs/series?season_id=" + selId);
      const results = data.results || [];
      const finals = results.find((r) => r.round_number === 4);
      const confs = results.filter((r) => r.round_number === 3);

      const seasonOptions = opts
        .map(
          (s) =>
            '<option value="' + s.season_id + '"' +
            (Number(s.season_id) === selId ? " selected" : "") + ">" +
            HI_(s.label || s.formatted_id || s.season_id) + "</option>"
        )
        .join("");

      const bracket =
        results.length
          ? '<div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px;">' +
            confs.map(seriesCard).join("") +
            (finals ? seriesCard(finals) : "") +
            "</div>"
          : '<div class="empty"><h4>No series restored for ' + HI_(selId) + "</h4>" +
            "<p>This season predates the restored conference finals (1993-94 onward), or the playoff history hasn't been rebuilt yet.</p></div>";

      return {
        html:
          '<h1 class="page-title">Playoff History</h1>' +
          '<p class="page-sub">Authoritative series results from the database — winners and scores are recorded, never inferred from standings.</p>' +
          '<div class="row wrap" style="align-items:center;gap:12px;margin-bottom:16px;">' +
          '<select class="field" id="po-season" style="width:190px;height:38px;">' + seasonOptions + "</select>" +
          '<span class="pill-tag">' + L(results.length) + " series</span></div>" +
          bracket +
          '<p class="panel-tip" style="margin-top:18px;">Conference finals are restored for the 16-team playoff era (1993-94 through today). First- and second-round series are not yet in the database.</p>',
        bind(view) {
          const sel = view.querySelector("#po-season");
          sel.addEventListener("change", () => {
            location.hash = "#/playoffs?season=" + sel.value;
          });
        },
      };
    } catch (err) {
      return "<div class='error-block'>" + HI_(err && err.message) + "</div>";
    }
  }

  window.HI_Playoffs = playoffs;
})();