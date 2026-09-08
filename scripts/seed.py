#!/usr/bin/env python3
"""Seed the Hockey Intelligence database from the NHL provider.

Usage:
    python scripts/seed.py [season_ids...]
    python scripts/seed.py 20152016 20242025
"""
import asyncio
import logging
import sys

from app.data.seeder import DataSeeder, ensure_data_source
from app.database.connection import async_session_factory, init_db

logging.basicConfig(level=logging.INFO)


async def main():
    await init_db()
    seasons = [int(s) for s in sys.argv[1:]] or None
    async with async_session_factory() as session:
        await ensure_data_source(session)
        await session.commit()
    seeder = DataSeeder()
    stats = await seeder.run(seasons)
    print(f"\nSeed complete: {stats}")


if __name__ == "__main__":
    asyncio.run(main())
