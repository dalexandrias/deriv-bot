from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    from app.main import _app_state
    async with _app_state.session_factory() as session:
        yield session
