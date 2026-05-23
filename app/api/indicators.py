from fastapi import APIRouter
from app.api.schemas import IndicatorCreate, IndicatorUpdate

router = APIRouter(prefix="/indicators", tags=["indicators"])


@router.get("/")
async def list_indicators():
    from app.db.models import IndicatorConfig
    from sqlalchemy import select
    from app.main import _app_state
    stmt = select(IndicatorConfig)
    result = await _app_state.db_session.execute(stmt)
    indicators = [
        {"id": i.id, "name": i.name, "indicator_type": i.indicator_type,
         "parameters": i.parameters, "enabled": i.enabled}
        for i in result.scalars().all()
    ]
    return {"data": indicators, "error": None}


@router.post("/")
async def create_indicator(body: IndicatorCreate):
    from app.db.models import IndicatorConfig
    from app.main import _app_state
    ind = IndicatorConfig(
        name=body.name, indicator_type=body.indicator_type,
        parameters=body.parameters, enabled=body.enabled,
    )
    _app_state.db_session.add(ind)
    await _app_state.db_session.commit()
    return {"data": {"id": ind.id, "name": ind.name}, "error": None}


@router.patch("/{indicator_id}")
async def update_indicator(indicator_id: int, body: IndicatorUpdate):
    from app.db.models import IndicatorConfig
    from app.main import _app_state
    ind = await _app_state.db_session.get(IndicatorConfig, indicator_id)
    if not ind:
        return {"data": None, "error": "Indicator not found"}
    if body.parameters is not None:
        ind.parameters = body.parameters
    if body.enabled is not None:
        ind.enabled = body.enabled
    await _app_state.db_session.commit()
    return {"data": {"id": ind.id, "name": ind.name}, "error": None}


@router.delete("/{indicator_id}")
async def delete_indicator(indicator_id: int):
    from app.db.models import IndicatorConfig
    from app.main import _app_state
    ind = await _app_state.db_session.get(IndicatorConfig, indicator_id)
    if not ind:
        return {"data": None, "error": "Indicator not found"}
    await _app_state.db_session.delete(ind)
    await _app_state.db_session.commit()
    return {"data": {"deleted": indicator_id}, "error": None}


@router.post("/reset-defaults")
async def reset_indicators():
    from app.db.models import IndicatorConfig
    from app.config import DEFAULT_INDICATORS
    from app.main import _app_state
    from sqlalchemy import delete
    await _app_state.db_session.execute(delete(IndicatorConfig))
    for default in DEFAULT_INDICATORS:
        _app_state.db_session.add(IndicatorConfig(**default))
    await _app_state.db_session.commit()
    return {"data": {"reset": True}, "error": None}
