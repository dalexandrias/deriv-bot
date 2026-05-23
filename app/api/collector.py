from fastapi import APIRouter
from app.api.schemas import CollectorConfigUpdate

router = APIRouter(prefix="/collector", tags=["collector"])


@router.get("/status")
async def collector_status():
    from app.main import _app_state
    if _app_state.collector:
        return {"data": {
            "running": _app_state.collector.is_running,
            "symbols": _app_state.collector.symbols,
            "timeframes": _app_state.collector.timeframes,
        }, "error": None}
    return {"data": {"running": False}, "error": None}


@router.patch("/config")
async def update_collector_config(body: CollectorConfigUpdate):
    from app.main import _app_state
    if _app_state.collector:
        symbols = body.symbols or _app_state.collector.symbols
        timeframes = body.timeframes or _app_state.collector.timeframes
        await _app_state.collector.update_config(symbols, timeframes)
    return {"data": {"status": "updated"}, "error": None}
