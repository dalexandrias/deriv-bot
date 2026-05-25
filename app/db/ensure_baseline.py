"""
Stamp the DB at 001_initial when tables already exist but alembic_version does not.
This handles the case where the schema was bootstrapped via create_all before
Alembic migrations were added to the startup sequence.
"""
import asyncio
import os

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


async def _run() -> None:
    url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://localhost/deriv")
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            has_version = await conn.scalar(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_name = 'alembic_version'"
            ))
            if has_version:
                return  # Alembic already tracking — nothing to do

            has_tables = await conn.scalar(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_name = 'bot_config'"
            ))
            if not has_tables:
                return  # Fresh DB — let Alembic create everything from scratch

            # Existing DB without Alembic tracking: stamp at the baseline revision
            # so that only newer migrations (002+) will be applied.
            await conn.execute(text(
                "CREATE TABLE alembic_version ("
                "  version_num VARCHAR(32) NOT NULL, "
                "  CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)"
                ")"
            ))
            await conn.execute(text("INSERT INTO alembic_version VALUES ('001_initial')"))
            await conn.commit()
            print("Stamped existing DB as 001_initial for Alembic migration tracking.")
    finally:
        await engine.dispose()


asyncio.run(_run())
