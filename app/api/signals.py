from fastapi import APIRouter

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("/")
async def list_signals(limit: int = 20, outcome: str | None = None, direction: str | None = None):
    from app.main import _app_state
    signals = await _app_state.repo.get_signals_filtered(limit=limit, outcome=outcome, direction=direction)
    return {"data": signals, "error": None}


@router.get("/stats")
async def signal_stats():
    from app.main import _app_state
    stats = await _app_state.repo.get_overall_stats()
    return {"data": stats, "error": None}


@router.get("/{signal_id}")
async def get_signal(signal_id: int):
    from app.main import _app_state
    from app.signals.repository import _orm_to_dict
    sig = await _app_state.repo.get_signal_by_id(signal_id)
    if not sig:
        return {"data": None, "error": "Signal not found"}
    return {"data": _orm_to_dict(sig), "error": None}
