from fastapi import APIRouter, Query

router = APIRouter(prefix="/candles", tags=["candles"])


@router.get("/")
async def list_candles(
    symbol: str = Query(default="R_25"),
    timeframe: str = Query(default="5m"),
    limit: int = Query(default=100, le=500),
):
    from app.main import _app_state

    candles = await _app_state.repo.get_candles_range(symbol, timeframe, count=limit)
    candles_with_meta = [
        {**c, "symbol": symbol, "timeframe": timeframe}
        for c in candles
    ]
    return {"data": candles_with_meta, "error": None}


@router.get("/symbols")
async def list_symbols():
    from app.db.models import Candle
    from sqlalchemy import select, distinct
    from app.main import _app_state

    result = await _app_state.db_session.execute(
        select(distinct(Candle.symbol)).order_by(Candle.symbol)
    )
    symbols = [row[0] for row in result.all()]
    return {"data": symbols, "error": None}
