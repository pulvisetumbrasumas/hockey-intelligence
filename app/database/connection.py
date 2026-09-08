from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,
    connect_args={"check_same_thread": False},
)

@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_busy_timeout(dbapi_conn, _record):
    """Queue writers politely instead of failing while the seeder holds the lock."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA busy_timeout = 30000")
    cursor.close()

async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
