from fastapi import APIRouter
from sqlalchemy import text

router = APIRouter()


@router.get("/health")
async def health_check():
    from app.main import _app_state
    db_ok = False
    deriv_ok = False
    try:
        if _app_state.session_factory:
            async with _app_state.session_factory() as session:
                await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        pass
    try:
        if _app_state.deriv_client:
            deriv_ok = _app_state.deriv_client.is_connected
    except Exception:
        pass
    return {"data": {"db": "ok" if db_ok else "error", "deriv_ws": "ok" if deriv_ok else "disconnected"}, "error": None}
