from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.api.schemas import IndicatorCreate, IndicatorUpdate
from app.api.deps import get_session
from app.db.models import IndicatorConfig

router = APIRouter(prefix="/indicators", tags=["indicators"])


@router.get("/")
async def list_indicators(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(IndicatorConfig))
    indicators = [
        {"id": i.id, "name": i.name, "indicator_type": i.indicator_type,
         "parameters": i.parameters, "enabled": i.enabled}
        for i in result.scalars().all()
    ]
    return {"data": indicators, "error": None}


@router.post("/")
async def create_indicator(body: IndicatorCreate, session: AsyncSession = Depends(get_session)):
    ind = IndicatorConfig(
        name=body.name, indicator_type=body.indicator_type,
        parameters=body.parameters, enabled=body.enabled,
    )
    session.add(ind)
    await session.commit()
    return {"data": {"id": ind.id, "name": ind.name}, "error": None}


@router.patch("/{indicator_id}")
async def update_indicator(indicator_id: int, body: IndicatorUpdate, session: AsyncSession = Depends(get_session)):
    ind = await session.get(IndicatorConfig, indicator_id)
    if not ind:
        return {"data": None, "error": "Indicator not found"}
    if body.parameters is not None:
        ind.parameters = body.parameters
    if body.enabled is not None:
        ind.enabled = body.enabled
    await session.commit()
    return {"data": {"id": ind.id, "name": ind.name}, "error": None}


@router.delete("/{indicator_id}")
async def delete_indicator(indicator_id: int, session: AsyncSession = Depends(get_session)):
    ind = await session.get(IndicatorConfig, indicator_id)
    if not ind:
        return {"data": None, "error": "Indicator not found"}
    await session.delete(ind)
    await session.commit()
    return {"data": {"deleted": indicator_id}, "error": None}


@router.post("/reset-defaults")
async def reset_indicators(session: AsyncSession = Depends(get_session)):
    from app.config import DEFAULT_INDICATORS
    await session.execute(delete(IndicatorConfig))
    for default in DEFAULT_INDICATORS:
        session.add(IndicatorConfig(**default))
    await session.commit()
    return {"data": {"reset": True}, "error": None}
