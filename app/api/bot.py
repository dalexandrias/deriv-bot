from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.db.models import BotConfig

router = APIRouter(prefix="/bot", tags=["bot"])


@router.post("/start")
async def start_bot():
    from app.main import _app_state
    if _app_state.agent and _app_state.agent.is_running:
        return {"data": {"status": "already_running"}, "error": None}
    if _app_state.agent:
        await _app_state.agent.start()
    return {"data": {"status": "started"}, "error": None}


@router.post("/stop")
async def stop_bot():
    from app.main import _app_state
    if _app_state.agent:
        await _app_state.agent.stop()
    return {"data": {"status": "stopped"}, "error": None}


@router.get("/status")
async def bot_status():
    from app.main import _app_state
    if _app_state.agent:
        return {"data": _app_state.agent.status, "error": None}
    return {"data": {"running": False}, "error": None}


@router.get("/config")
async def get_bot_config(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(BotConfig))
    configs = {c.key: c.value for c in result.scalars().all()}
    return {"data": configs, "error": None}


@router.patch("/config")
async def update_bot_config(body: dict, session: AsyncSession = Depends(get_session)):
    for key, value in body.items():
        result = await session.execute(select(BotConfig).where(BotConfig.key == key))
        cfg = result.scalar_one_or_none()
        if cfg:
            cfg.value = value
        else:
            session.add(BotConfig(key=key, value=value))
    await session.commit()
    return {"data": {"updated": list(body.keys())}, "error": None}
