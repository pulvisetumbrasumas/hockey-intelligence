#!/usr/bin/env python3
"""Backfill realtime gameplay counters (takeaways, giveaways, hits, blocked).

Usage:
    python scripts/seed_realtime_stats.py [start_season]

Defaults to 2007-08 — the first season the NHL tracked these counters — and
walks every later season present in the database. Idempotent: re-runs update
existing rows in place.

Note: pre-2007 seasons have no realtime data anywhere; the NHL did not track
takeaways/hits/blocked shots then, so older careers show blanks rather than
zeros.
"""
import asyncio
import logging
import sys

from sqlalchemy import select
from sqlalchemy.sql import func

from app.core.config import get_settings
from app.data.seeder import DataSeeder
from app.database.connection import async_session_factory
from app.models import Season

logging.basicConfig(level=logging.WARNING)


async def main():
    settings = get_settings()
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 20072008

    async with async_session_factory() as session:
        season_ids = set((await session.execute(select(Season.id))).scalars().all())
    seasons = sorted(s for s in season_ids if s >= start)

    seeder = DataSeeder()
    total: dict = {}
    for season_id in seasons:
        async with async_session_factory() as session:
            total = await seeder.import_realtime_stats(session, [season_id])
            await session.commit()
        print(f"{season_id}: {total}")

    print(f"\nRealtime backfill complete for {len(seasons)} seasons: {total}")


if __name__ == "__main__":
    asyncio.run(main())