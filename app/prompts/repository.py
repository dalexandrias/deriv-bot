"""Repository for managing prompt versions."""

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PromptVersion


async def get_active(session: AsyncSession) -> PromptVersion | None:
    """Fetch the currently active prompt version."""
    stmt = select(PromptVersion).where(PromptVersion.is_active == True)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_recent(session: AsyncSession, limit: int = 10) -> list[PromptVersion]:
    """Fetch the most recent prompt versions (ordered by created_at DESC)."""
    stmt = select(PromptVersion).order_by(desc(PromptVersion.created_at)).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()


async def save_new(
    session: AsyncSession, content: str, note: str | None = None
) -> PromptVersion:
    """
    Save a new prompt version as active.

    Steps:
    1. Mark all existing versions as inactive.
    2. Insert new active version.
    3. After commit, prune to keep only 10 most recent (never delete the active one).
    """
    stmt = select(PromptVersion).where(PromptVersion.is_active == True)
    result = await session.execute(stmt)
    for prompt in result.scalars():
        prompt.is_active = False

    new_prompt = PromptVersion(content=content, is_active=True, note=note)
    session.add(new_prompt)
    await session.flush()

    stmt = select(func.count(PromptVersion.id))
    result = await session.execute(stmt)
    count = result.scalar()

    if count > 10:
        excess = count - 10
        stmt = (
            select(PromptVersion)
            .where(PromptVersion.is_active == False)
            .order_by(PromptVersion.created_at)
            .limit(excess)
        )
        result = await session.execute(stmt)
        for prompt in result.scalars():
            await session.delete(prompt)

    await session.commit()
    return new_prompt


async def restore(session: AsyncSession, version_id: int) -> PromptVersion | None:
    """Restore an older prompt version (creates a new active version from it)."""
    stmt = select(PromptVersion).where(PromptVersion.id == version_id)
    result = await session.execute(stmt)
    old_prompt = result.scalar_one_or_none()

    if not old_prompt:
        return None

    return await save_new(session, old_prompt.content, note=f"restaurada da v{version_id}")
