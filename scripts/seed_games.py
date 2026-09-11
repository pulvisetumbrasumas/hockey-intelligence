#!/usr/bin/env python3
"""Seed per-game results and playoff early-round series.

Usage:
    python scripts/seed_games.py [season_ids...]

Two jobs run in one pass:

1. **Games** — every finalized regular-season and playoff game is stored in the
   ``games`` table for the given seasons (default: the configured seed seasons,
   i.e. the 2015-16 → 2024-25 window). Idempotent: re-runs add nothing.

2. **Playoff rounds 1-2** — first- and second-round playoff series are
   reconstructed from the finalized playoff games for EVERY 16-team-era season
   (1993-94 onward) present in the database, completing the bracket alongside
   the authoritative conference finals and Stanley Cup Final.
"""
import asyncio
import logging
import sys

from sqlalchemy import select

from app.core.config import get_settings
from app.data.seeder import DataSeeder
from app.database.connection import async_session_factory
from app.models import Season

logging.basicConfig(level=logging.INFO)


async def main():
    settings = get_settings()
    args = [int(s) for s in sys.argv[1:]]
    game_seasons = args or settings.seed_seasons

    async with async_session_factory() as session:
        season_ids = set((await session.execute(select(Season.id))).scalars().all())
    series_seasons = sorted(s for s in season_ids if 19931994 <= s <= 20262027)

    seeder = DataSeeder()
    stats: dict = {}
    async with async_session_factory() as session:
        stats.update(await seeder.import_games(session, game_seasons))
        await session.commit()
    async with async_session_factory() as session:
        stats.update(await seeder.import_playoff_series(session, series_seasons))
        await session.commit()

    print(f"\nSchedule seed complete: {stats}")


if __name__ == "__main__":
    asyncio.run(main())
