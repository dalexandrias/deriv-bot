"""Repository for agent memory (cycles, lessons, reflections).

Module-level async functions following the prompts/repository.py pattern.
"""
from datetime import datetime, timezone

from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgentCycle, AgentLesson, AgentReflection
from app.agent.memory_models import CycleCreate


async def insert_cycle(session: AsyncSession, data: CycleCreate) -> int:
    cycle = AgentCycle(
        cycle_number=data.cycle_number,
        symbol=data.symbol,
        regime=data.regime,
        m15_bias=data.m15_bias,
        time_window=data.time_window,
        confluence_call=data.confluence_call,
        confluence_put=data.confluence_put,
        llm_direction=data.llm_direction,
        llm_confidence=data.llm_confidence,
        llm_rationale=data.llm_rationale,
        llm_raw_response=data.llm_raw_response,
        emitted=data.emitted,
        signal_id=data.signal_id,
        skip_reason=data.skip_reason,
    )
    session.add(cycle)
    await session.flush()
    return cycle.id


async def get_recent_cycles(session: AsyncSession, limit: int = 5) -> list[dict]:
    stmt = (
        select(AgentCycle)
        .order_by(desc(AgentCycle.id))
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [_cycle_to_dict(c) for c in result.scalars().all()]


async def get_active_lessons(session: AsyncSession, limit: int = 5) -> list[dict]:
    stmt = (
        select(AgentLesson)
        .where(AgentLesson.is_active == True)
        .order_by(desc(AgentLesson.confidence), desc(AgentLesson.last_reinforced_at))
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [_lesson_to_dict(l) for l in result.scalars().all()]


async def query_lessons_by_topic(
    session: AsyncSession, topic_prefix: str, limit: int = 10
) -> list[dict]:
    stmt = (
        select(AgentLesson)
        .where(AgentLesson.topic.startswith(topic_prefix))
        .order_by(desc(AgentLesson.confidence))
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [_lesson_to_dict(l) for l in result.scalars().all()]


async def upsert_lessons(
    session: AsyncSession, reflection_id: int, lessons: list[dict]
) -> None:
    now = datetime.now(timezone.utc)

    for lesson in lessons:
        topic = lesson.get("topic", "")
        content = lesson.get("content", "")

        if not topic or not content:
            continue

        stmt = select(AgentLesson).where(
            and_(
                AgentLesson.topic == topic,
                AgentLesson.is_active == True,
            )
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.content = content
            existing.confidence = lesson.get("confidence", existing.confidence)
            existing.sample_size = lesson.get("sample_size", existing.sample_size)
            existing.last_reinforced_at = now
            existing.updated_at = now
            existing.reflection_id = reflection_id
        else:
            session.add(
                AgentLesson(
                    content=content,
                    topic=topic,
                    sample_size=lesson.get("sample_size", 0),
                    confidence=lesson.get("confidence", 0.5),
                    is_active=True,
                    last_reinforced_at=now,
                    reflection_id=reflection_id,
                )
            )


async def insert_reflection(
    session: AsyncSession,
    cycles_analyzed: int,
    model_used: str,
    trigger: str,
    raw_response: str,
) -> int:
    reflection = AgentReflection(
        cycles_analyzed=cycles_analyzed,
        model_used=model_used,
        trigger=trigger,
        raw_response=raw_response,
    )
    session.add(reflection)
    await session.flush()
    return reflection.id


async def count_cycles_since(
    session: AsyncSession, reflection_id: int | None = None
) -> int:
    stmt = select(func.count(AgentCycle.id))
    if reflection_id is not None:
        last = await get_reflection_by_id(session, reflection_id)
        if last:
            stmt = stmt.where(AgentCycle.created_at > last.created_at)
    result = await session.execute(stmt)
    return result.scalar() or 0


async def get_last_reflection(session: AsyncSession) -> AgentReflection | None:
    stmt = select(AgentReflection).order_by(desc(AgentReflection.id)).limit(1)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_reflection_by_id(
    session: AsyncSession, reflection_id: int
) -> AgentReflection | None:
    stmt = select(AgentReflection).where(AgentReflection.id == reflection_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def _cycle_to_dict(c: AgentCycle) -> dict:
    return {
        "id": c.id,
        "cycle_number": c.cycle_number,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "symbol": c.symbol,
        "regime": c.regime,
        "m15_bias": c.m15_bias,
        "time_window": c.time_window,
        "confluence_call": c.confluence_call,
        "confluence_put": c.confluence_put,
        "llm_direction": c.llm_direction,
        "llm_confidence": c.llm_confidence,
        "llm_rationale": c.llm_rationale,
        "llm_raw_response": c.llm_raw_response,
        "emitted": c.emitted,
        "signal_id": c.signal_id,
        "skip_reason": c.skip_reason,
    }


def _lesson_to_dict(l: AgentLesson) -> dict:
    return {
        "id": l.id,
        "content": l.content,
        "topic": l.topic,
        "sample_size": l.sample_size,
        "confidence": l.confidence,
        "is_active": l.is_active,
        "last_reinforced_at": (
            l.last_reinforced_at.isoformat() if l.last_reinforced_at else None
        ),
        "reflection_id": l.reflection_id,
    }
