from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
import os


class Base(DeclarativeBase):
    pass


def create_engine_and_session(database_url: str | None = None):
    url = database_url or os.environ.get("DATABASE_URL", "postgresql+asyncpg://localhost/deriv")
    engine = create_async_engine(url, echo=False, pool_size=10, max_overflow=20)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return engine, session_factory
