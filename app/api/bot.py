from fastapi import APIRouter
from sqlalchemy import select

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
async def get_bot_config():
    from app.db.models import BotConfig
    from app.main import _app_state
    stmt = select(BotConfig)
    result = await _app_state.db_session.execute(stmt)
    configs = {c.key: c.value for c in result.scalars().all()}
    return {"data": configs, "error": None}


@router.patch("/config")
async def update_bot_config(body: dict):
    from app.db.models import BotConfig
    from sqlalchemy import select
    from app.main import _app_state
    for key, value in body.items():
        stmt = select(BotConfig).where(BotConfig.key == key)
        result = await _app_state.db_session.execute(stmt)
        cfg = result.scalar_one_or_none()
        if cfg:
            cfg.value = value
        else:
            _app_state.db_session.add(BotConfig(key=key, value=value))
    await _app_state.db_session.commit()
    return {"data": {"updated": list(body.keys())}, "error": None}
