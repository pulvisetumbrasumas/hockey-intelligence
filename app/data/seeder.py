from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.database.connection import async_session_factory
from app.models import (
    DataImport,
    DataSource,
    Franchise,
    Game,
    GoalieSeasonStats,
    Player,
    PlayerSeasonStats,
    PlayoffSeries,
    Season,
    Team,
    TeamIdentity,
    TeamSeasonStats,
)
from app.providers.nhl_provider import NHLDataProvider
from app.services.playoffs import reconstruct_early_rounds

logger = logging.getLogger(__name__)

GAME_TYPE_LABELS = {2: "regular", 3: "playoffs"}


class DataSeeder:
    """Ingestion pipeline from the NHL provider into the normalized database.

    Records provenance in data_imports for every fetch. Respects the provider
    interface so alternative providers can be swapped in later.
    """

    def __init__(self, provider: NHLDataProvider | None = None):
        self.provider = provider or NHLDataProvider()
        self.settings = get_settings()

    async def run(self, seasons: list[int] | None = None) -> dict:
        target_seasons = seasons or self.settings.seed_seasons
        stats: dict[str, int] = {}
        async with async_session_factory() as session:
            stats.update(await self.import_franchises(session))
            stats.update(await self.import_teams(session))
            stats.update(await self.import_seasons(session))
            for season_id in target_seasons:
                stats.update(await self.import_season_stats(session, season_id))
            stats.update(await self.import_realtime_stats(session, target_seasons))
            stats.update(await self.import_missing_bios(session))
            stats.update(await self.import_playoff_stats(session, target_seasons))
            await session.commit()
        return stats

    async def import_franchises(self, session: AsyncSession) -> dict:
        franchises = await self.provider.get_franchises()
        count = 0
        for f in franchises:
            done = await self._get_or_create(
                session, Franchise, id=f["id"]
            )
            if done is None:
                continue
            done.full_name = f.get("fullName")
            done.common_name = f.get("teamCommonName")
            done.place_name = f.get("teamPlaceName")
            count += 1
        await session.flush()
        await self._record_import(session, "franchises", len(franchises), url="franchise")
        return {"franchises": count}

    async def import_teams(self, session: AsyncSession) -> dict:
        teams = await self.provider.get_teams()
        count = 0
        for t in teams:
            team = await self._get_or_create(session, Team, id=t["id"])
            if team is None:
                continue
            team.nhl_id = t.get("id")
            team.franchise_id = t.get("franchiseId")
            team.full_name = t.get("fullName")
            team.abbreviation = t.get("triCode")
            team.tricode = t.get("triCode")
            team.active = 1 if t.get("franchiseId") else 0
            count += 1
            # Create or refresh a TeamIdentity row reflecting the official identity
            existing = await self._find_identity(session, t["id"])
            city = (
                (t.get("fullName") or "").rsplit(" ", 1)[0]
                if " " in (t.get("fullName") or "")
                else ""
            )
            if existing is None:
                session.add(
                    TeamIdentity(
                        team_id=t["id"],
                        franchise_id=t.get("franchiseId"),
                        name=t.get("fullName"),
                        city=city,
                        abbr=t.get("triCode"),
                    )
                )
            else:
                existing.franchise_id = t.get("franchiseId")
                existing.name = t.get("fullName")
                existing.city = city
                existing.abbr = t.get("triCode")
        await session.flush()
        await self._record_import(session, "teams", len(teams), url="team")
        return {"teams": count}

    async def _find_identity(self, session: AsyncSession, team_id: int) -> TeamIdentity | None:
        result = await session.execute(
            select(TeamIdentity).where(TeamIdentity.team_id == team_id)
        )
        return result.scalars().first()

    async def import_seasons(self, session: AsyncSession) -> dict:
        seasons = await self.provider.get_seasons()
        count = 0
        for s in seasons:
            season = await self._get_or_create(session, Season, id=s["id"])
            if season is None:
                continue
            season.formatted_id = s.get("formattedSeasonId")
            season.start_date = self._parse_iso(s.get("startDate"))
            season.regular_season_end_date = self._parse_iso(
                s.get("regularSeasonEndDate")
            )
            season.end_date = self._parse_iso(s.get("endDate"))
            season.regular_season_games = s.get("numberOfGames")
            season.total_regular_season_games = s.get("totalRegularSeasonGames")
            season.total_playoff_games = s.get("totalPlayoffGames")
            season.season_ordinal = s.get("seasonOrdinal")
            season.ties_used = s.get("tiesInUse")
            season.ot_loss_point = s.get("pointForOTLossInUse")
            season.wildcard_used = s.get("wildcardInUse")
            count += 1
        await session.flush()
        await self._record_import(session, "seasons", len(seasons), url="season")
        return {"seasons": count}

    async def import_season_stats(self, session: AsyncSession, season_id: int) -> dict:
        counts = {"skaters": 0, "goalies": 0, "teams": 0}
        season_exists = await self._get_or_create(session, Season, id=season_id)
        if season_exists is None:
            return counts

        start = 0
        limit = 200
        while True:
            skaters, total = await self.provider.get_skater_stats(
                season_id, 2, start, limit
            )
            for s in skaters:
                await self._upsert_skater(session, s, season_id)
            counts["skaters"] += len(skaters)
            if not skaters or start + len(skaters) >= total:
                break
            start += len(skaters)

        start = 0
        while True:
            goalies, total = await self.provider.get_goalie_stats(
                season_id, 2, start, limit
            )
            for g in goalies:
                await self._upsert_goalie(session, g, season_id)
            counts["goalies"] += len(goalies)
            if not goalies or start + len(goalies) >= total:
                break
            start += len(goalies)

        start = 0
        while True:
            teams, total = await self.provider.get_team_stats(
                season_id, 2, start, limit
            )
            for t in teams:
                await self._upsert_team_stats(session, t, season_id)
            counts["teams"] += len(teams)
            if not teams or start + len(teams) >= total:
                break
            start += len(teams)

        await session.flush()
        await self._record_import(
            session, "player_season_stats", season_id, url="skater/summary"
        )
        return counts

    async def import_missing_bios(self, session: AsyncSession) -> dict:
        """Fetch bios for players missing biographical data via the web API."""
        result = await session.execute(
            select(Player).where(Player.birth_country.is_(None)).limit(500)
        )
        players = result.scalars().all()
        if not players:
            return {"bios": 0}
        ids = [p.id for p in players]
        return await self.import_player_bios(session, ids)

    async def import_realtime_stats(
        self, session: AsyncSession, seasons: list[int]
    ) -> dict:
        """Backfill possession/physicality counters from ``skater/realtime``.

        The summary endpoints do not report takeaways, giveaways, hits or
        blocked shots; the realtime endpoint does. These counters were never
        tracked before the 2007-08 season, so older seasons return no rows and
        the existing stats are left untouched.
        """
        counts = {"takeaways": 0, "giveaways": 0, "hits": 0, "blocked_shots": 0}
        limit = 200
        for season_id in seasons:
            start = 0
            while True:
                rows, total = await self.provider.get_skater_realtime_stats(
                    season_id, 2, start, limit
                )
                for s in rows:
                    stat = await self._get_or_create_stat(
                        session, s.get("playerId"), season_id, 2, PlayerSeasonStats
                    )
                    if stat is None:
                        continue
                    for src, key in (
                        ("takeaways", "takeaways"),
                        ("giveaways", "giveaways"),
                        ("hits", "hits"),
                        ("blocked_shots", "blockedShots"),
                    ):
                        if s.get(key) is not None:
                            setattr(stat, src, s.get(key))
                            counts[src] += 1
                if not rows or start + len(rows) >= total:
                    break
                start += len(rows)
        await session.flush()
        await self._record_import(
            session, "realtime_stats", counts["takeaways"], url="skater/realtime"
        )
        return counts

    async def import_playoff_stats(
        self, session: AsyncSession, seasons: list[int]
    ) -> dict:
        """Import playoff (gameType 3) stats for the seeded seasons."""
        counts = {"playoff_skaters": 0, "playoff_goalies": 0}
        limit = 200
        for season_id in seasons:
            start = 0
            while True:
                skaters, total = await self.provider.get_skater_stats(
                    season_id, 3, start, limit
                )
                for s in skaters:
                    await self._upsert_skater(session, s, season_id, 3)
                counts["playoff_skaters"] += len(skaters)
                if not skaters or start + len(skaters) >= total:
                    break
                start += len(skaters)
            start = 0
            while True:
                goalies, total = await self.provider.get_goalie_stats(
                    season_id, 3, start, limit
                )
                for g in goalies:
                    await self._upsert_goalie(session, g, season_id, 3)
                counts["playoff_goalies"] += len(goalies)
                if not goalies or start + len(goalies) >= total:
                    break
                start += len(goalies)
        await session.flush()
        await self._record_import(
            session, "playoff_stats", counts["playoff_skaters"], url="skater/summary"
        )
        return counts

    async def import_games(self, session: AsyncSession, seasons: list[int]) -> dict:
        """Store every finalized regular-season and playoff game for a season.

        Uses the NHL game id as the primary key (it is globally unique and
        numerically fits), so re-runs are cheap and never duplicate rows.
        """
        count = upserted = 0
        for season_id in seasons:
            season = await session.get(Season, season_id)
            if season is None:
                continue
            existing_ids = set(
                (
                    await session.execute(
                        select(Game.id).where(Game.season_id == season_id)
                    )
                ).scalars()
            )
            for g in await self.provider.get_games(season_id):
                gid = g.get("id")
                if not gid or gid in existing_ids:
                    continue
                home = g.get("homeTeam") or {}
                away = g.get("awayTeam") or {}
                venue = g.get("venue")
                if isinstance(venue, dict):
                    venue = venue.get("default")
                period = g.get("periodDescriptor") or {}
                ot_sol = None
                if period.get("periodType") == "OT":
                    ot_sol = "OT"
                elif period.get("periodType") == "SO":
                    ot_sol = "SO"
                session.add(
                    Game(
                        id=gid,
                        season_id=g.get("season") or season_id,
                        game_type=g.get("gameType"),
                        game_date=self._parse_iso(g.get("startTimeUTC")),
                        home_team_id=home.get("id"),
                        away_team_id=away.get("id"),
                        home_team_code=(home.get("abbrev") or "")[:10],
                        away_team_code=(away.get("abbrev") or "")[:10],
                        home_score=home.get("score"),
                        away_score=away.get("score"),
                        venue=venue,
                        ot_sol=ot_sol,
                        attendance=g.get("attendance"),
                        status="final",
                    )
                )
                existing_ids.add(gid)
                count += 1
                if count % 500 == 0:
                    await session.flush()
            upserted += 1
        await session.flush()
        await self._record_import(session, "games", count, url="schedule")
        return {"games": count, "seasons": upserted}

    async def import_playoff_series(
        self, session: AsyncSession, seasons: list[int]
    ) -> dict:
        """Reconstruct first- and second-round series for the 16-team era.

        Round 1-2 entries are fully derived from finalized playoff games, so a
        previous set for a season is replaced deterministically rather than
        duplicated. Conference finals (round 3) and the Cup Final (champions)
        are authoritative and are never touched here.
        """
        series_seasons = [s for s in seasons if s >= 19931994]
        if not series_seasons:
            return {"playoff_series": 0, "seasons": 0}
        team_rows = (await session.execute(select(Team))).scalars().all()
        team_names = {t.id: (t.full_name or t.abbreviation) for t in team_rows}
        count = restored = 0
        for season_id in series_seasons:
            series_list = reconstruct_early_rounds(
                await self.provider.get_playoff_games(season_id)
            )
            if not series_list:
                continue
            rows = (
                await session.execute(
                    select(PlayoffSeries.id).where(
                        PlayoffSeries.season_id == season_id,
                        PlayoffSeries.round_number < 3,
                    )
                )
            ).scalars().all()
            for pid in rows:
                await session.delete(await session.get(PlayoffSeries, pid))
            for s in series_list:
                session.add(
                    PlayoffSeries(
                        season_id=s["season_id"],
                        round_number=s["round_number"],
                        round_label=s["round_label"],
                        conference=s["conference"],
                        winner_team_id=s["winner_team_id"],
                        winner_name=team_names.get(
                            s["winner_team_id"], s.get("winner_abbrev")
                        ),
                        loser_team_id=s["loser_team_id"],
                        loser_name=team_names.get(
                            s["loser_team_id"], s.get("loser_abbrev")
                        ),
                        winner_games=s["winner_games"],
                        loser_games=s["loser_games"],
                        note=None,
                    )
                )
                count += 1
            restored += 1
        await session.flush()
        await self._record_import(session, "playoff_series", count, url="schedule")
        return {"playoff_series": count, "seasons": restored}

    async def _upsert_skater(
        self, session: AsyncSession, s: dict, season_id: int, game_type: int = 2
    ) -> None:
        pid = s.get("playerId")
        if not pid:
            return
        player = await self._get_or_create(session, Player, id=pid)
        if player is not None:
            player.full_name = s.get("skaterFullName") or player.full_name
            player.last_name = s.get("lastName") or player.last_name
            player.position_code = s.get("positionCode") or player.position_code
            player.shoots_catches = s.get("shootsCatches") or player.shoots_catches

        stat = await self._get_or_create_stat(session, pid, season_id, game_type, PlayerSeasonStats)
        if stat is None:
            return
        stat.team_abbrevs = s.get("teamAbbrevs")
        stat.games_played = s.get("gamesPlayed")
        stat.goals = s.get("goals")
        stat.assists = s.get("assists")
        stat.points = s.get("points")
        stat.points_per_game = s.get("pointsPerGame")
        stat.plus_minus = s.get("plusMinus")
        stat.penalty_minutes = s.get("penaltyMinutes")
        stat.ev_goals = s.get("evGoals")
        stat.ev_points = s.get("evPoints")
        stat.pp_goals = s.get("ppGoals")
        stat.pp_points = s.get("ppPoints")
        stat.sh_goals = s.get("shGoals")
        stat.sh_points = s.get("shPoints")
        stat.game_winning_goals = s.get("gameWinningGoals")
        stat.ot_goals = s.get("otGoals")
        stat.shots = s.get("shots")
        stat.shooting_pct = s.get("shootingPct")
        stat.faceoff_win_pct = s.get("faceoffWinPct")
        stat.time_on_ice_per_game = s.get("timeOnIcePerGame")
        stat.is_goalie = 0

    async def _upsert_goalie(
        self, session: AsyncSession, g: dict, season_id: int, game_type: int = 2
    ) -> None:
        pid = g.get("playerId")
        if not pid:
            return
        player = await self._get_or_create(session, Player, id=pid)
        if player is not None:
            player.full_name = g.get("goalieFullName") or player.full_name
            player.last_name = g.get("lastName") or player.last_name
            player.position_code = "G"
            player.shoots_catches = g.get("shootsCatches") or player.shoots_catches
            player.is_goalie = 1

        stat = await self._get_or_create(
            session, GoalieSeasonStats, player_id=pid, season_id=season_id, game_type=game_type
        )
        if stat is None:
            return
        stat.team_abbrevs = g.get("teamAbbrevs")
        stat.games_played = g.get("gamesPlayed")
        stat.games_started = g.get("gamesStarted")
        stat.wins = g.get("wins")
        stat.losses = g.get("losses")
        stat.ot_losses = g.get("otLosses")
        stat.ties = g.get("ties")
        stat.goals_against = g.get("goalsAgainst")
        stat.shots_against = g.get("shotsAgainst")
        stat.saves = g.get("saves")
        stat.save_pct = g.get("savePct")
        stat.goals_against_average = g.get("goalsAgainstAverage")
        stat.shutouts = g.get("shutouts")
        stat.time_on_ice = g.get("timeOnIce")
        stat.goals = g.get("goals")
        stat.assists = g.get("assists")
        stat.points = g.get("points")
        stat.penalty_minutes = g.get("penaltyMinutes")

    async def _upsert_team_stats(self, session: AsyncSession, t: dict, season_id: int) -> None:
        tid = t.get("teamId")
        if not tid:
            return
        stat = await self._get_or_create(
            session, TeamSeasonStats, team_id=tid, season_id=season_id, game_type=2
        )
        if stat is None:
            return
        stat.games_played = t.get("gamesPlayed")
        stat.wins = t.get("wins")
        stat.losses = t.get("losses")
        stat.ot_losses = t.get("otLosses")
        stat.points = t.get("points")
        stat.goals_for = t.get("goalsFor")
        stat.goals_against = t.get("goalsAgainst")
        stat.power_play_pct = t.get("powerPlayPct")
        stat.penalty_kill_pct = t.get("penaltyKillPct")
        stat.power_play_goals = t.get("powerPlayGoals")
        stat.power_play_opportunities = t.get("powerPlayOpportunities")
        stat.shorthanded_goals = t.get("shorthandedGoals")
        stat.shots_per_game = t.get("shotsForPerGame")
        stat.shots_against_per_game = t.get("shotsAgainstPerGame")
        stat.faceoff_pct = t.get("faceoffWinPct")
        stat.penalty_minutes = t.get("penaltyMinutesPerGame")

    async def import_player_bios(
        self, session: AsyncSession, player_ids: list[int]
    ) -> dict:
        if not player_ids:
            return {"bios": 0}
        bios = await self.provider.get_player_bios(player_ids)
        count = 0
        for pid, bio in bios.items():
            player = await self.session_get(session, Player, pid)
            if not player:
                player = Player(id=pid)
                session.add(player)
            player.full_name = bio.get("fullName") or player.full_name
            first = bio.get("firstName")
            last = bio.get("lastName")
            if isinstance(first, dict):
                first = first.get("default")
            if isinstance(last, dict):
                last = last.get("default")
            player.first_name = first or player.first_name
            player.last_name = last or player.last_name
            player.position_code = bio.get("position") or player.position_code
            setattr(player, "birth_date", self._parse_iso(bio.get("birthDate")))
            city = bio.get("birthCity")
            if isinstance(city, dict):
                city = city.get("default")
            player.birth_city = city or player.birth_city
            player.birth_country = bio.get("birthCountry") or player.birth_country
            if bio.get("heightInInches"):
                h = bio["heightInInches"]
                setattr(player, "height", f"{h // 12}'{h % 12}\"")
            if bio.get("weightInPounds"):
                player.weight = bio["weightInPounds"]
            player.shoots_catches = bio.get("shootsCatches") or player.shoots_catches
            draft = bio.get("draftDetails") or {}
            player.draft_year = draft.get("year") or player.draft_year
            player.draft_round = draft.get("round") or player.draft_round
            player.draft_overall = draft.get("number") or player.draft_overall
            count += 1
        await session.flush()
        await self._record_import(session, "player_bios", count, url="player/landing")
        return {"bios": count}

    async def session_get(self, session: AsyncSession, model, key: int):
        return await session.get(model, key)

    # ------------------------------------------------------------------ utils

    async def _get_or_create(self, session: AsyncSession, model, **kwargs):
        result = await session.execute(select(model).filter_by(**kwargs))
        obj = result.scalars().first()
        if obj is None:
            obj = model(**kwargs)
            session.add(obj)
            # No flush here: callers assign their attributes and a later
            # SELECT triggers autoflush with the fully-populated row.
        return obj

    async def _get_or_create_stat(self, session, pid, season_id, game_type, model):
        result = await session.execute(
            select(model).filter_by(
                player_id=pid, season_id=season_id, game_type=game_type
            )
        )
        stat = result.scalars().first()
        if stat is None:
            stat = model(player_id=pid, season_id=season_id, game_type=game_type)
            session.add(stat)
        return stat

    async def _record_import(
        self, session: AsyncSession, data_type: str, row_count: int, url: str = ""
    ) -> None:
        session.add(
            DataImport(
                source_id=1,
                data_type=data_type,
                row_count=row_count,
                imported_at=datetime.utcnow(),
                status="success",
                url=url,
            )
        )

    @staticmethod
    def _parse_iso(value: str | None):
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None


async def ensure_data_source(session: AsyncSession) -> None:
    result = await session.execute(select(DataSource).where(DataSource.id == 1))
    if result.scalars().first() is None:
        session.add(
            DataSource(
                id=1,
                name="NHL Stats & Web API",
                url="https://api.nhle.com/stats/rest/en",
                description=(
                    "Public NHL statistics and web API. Provides season-level "
                    "player, goalie, and team statistics plus player bios."
                ),
                source_type="api",
                license_notes=(
                    "NHL public API. Redistribution and commercial use should be "
                    "reviewed against NHL terms."
                ),
            )
        )
        await session.flush()
