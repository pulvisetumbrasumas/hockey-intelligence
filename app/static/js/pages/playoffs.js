/* ============================================================
   PLAYOFFS — restored bracket history (rounds 1-4)
   ============================================================ */
(function () {
  "use strict";
  const HI_ = window.HI.escape;
  const L = window.HI.fmtNum;
  const BLANK =
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3C/svg%3E";

  const ROUND_HEADERS = {
    1: "First round",
    2: "Second round",
    3: "Conference finals",
    4: "Stanley Cup Final",
  };

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
        : r.round_number === 3
          ? HI_(r.conference || "") + " Conference Final"
          : HI_(r.round_label || "Round " + r.round_number) +
            (r.conference ? ' <span class="muted">' + HI_(r.conference) + "</span>" : "");
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

      const byRound = {};
      results.forEach((r) => {
        (byRound[r.round_number] = byRound[r.round_number] || []).push(r);
      });

      const seasonOptions = opts
        .map(
          (s) =>
            '<option value="' + s.season_id + '"' +
            (Number(s.season_id) === selId ? " selected" : "") + ">" +
            HI_(s.label || s.formatted_id || s.season_id) + "</option>"
        )
        .join("");

      // Preserve round ordering even when a round is missing.
      const roundOrder = [1, 2, 3, 4].filter((r) => byRound[r] && byRound[r].length);
      const bracket = results.length
        ? roundOrder
            .map((r) => {
              const games = (byRound[r] || [])
                .slice()
                .sort((a, b) => (a.conference === "Eastern" ? -1 : 1));
              return (
                '<div class="section" style="margin-top:18px;"><div class="head"><h3>' +
                HI_(ROUND_HEADERS[r] || "Round " + r) + "</h3>" +
                '<span class="pill-tag cyan">' + L(games.length) + " series</span></div>" +
                '<div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px;">' +
                games.map(seriesCard).join("") +
                "</div></div>"
              );
            })
            .join("")
          : '<div class="empty"><h4>No series restored for ' + HI_(selId) + "</h4>" +
            "<p>This season predates the restored playoff history (1993-94 onward), or the bracket hasn't been rebuilt yet.</p></div>";

      return {
        html:
          '<h1 class="page-title">Playoff History</h1>' +
          '<p class="page-sub">Authoritative series results from the database — winners and scores are recorded, never inferred from standings.</p>' +
          '<div class="row wrap" style="align-items:center;gap:12px;margin-bottom:16px;">' +
          '<select class="field" id="po-season" style="width:190px;height:38px;">' + seasonOptions + "</select>" +
          '<span class="pill-tag">' + L(results.length) + " series</span></div>" +
          bracket +
          '<p class="panel-tip" style="margin-top:18px;">Round 1-2 results are rebuilt from finalized playoff games on record; conference finals and the Cup Final are authoritative reference data. All 16-team-era seasons (1993-94 through today) are covered.</p>',
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