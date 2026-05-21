from deriv.client import DerivClient

TIMEFRAME_TO_GRANULARITY = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
}


async def get_candles(client: DerivClient, symbol: str, timeframe: str, count: int = 20) -> list[dict]:
    granularity = TIMEFRAME_TO_GRANULARITY.get(timeframe)
    if granularity is None:
        raise ValueError(f"Timeframe inválido: {timeframe}")
    resp = await client._send({
        "ticks_history": symbol,
        "style": "candles",
        "granularity": granularity,
        "count": count,
        "end": "latest",
    })
    candles = resp.get("candles", [])
    return [
        {
            "time": c["epoch"],
            "open": float(c["open"]),
            "high": float(c["high"]),
            "low": float(c["low"]),
            "close": float(c["close"]),
        }
        for c in candles
    ]


async def get_tick(client: DerivClient, symbol: str) -> float:
    # Use ticks_history (one-shot) instead of ticks (subscription) to avoid AlreadySubscribed
    resp = await client._send({
        "ticks_history": symbol,
        "end": "latest",
        "count": 1,
        "style": "ticks",
    })
    prices = resp.get("history", {}).get("prices", [])
    if not prices:
        raise RuntimeError(f"get_tick: nenhum preço retornado para {symbol}")
    return float(prices[-1])


async def get_active_symbols(client: DerivClient) -> list[dict]:
    resp = await client._send({"active_symbols": "brief", "product_type": "basic"})
    return resp.get("active_symbols", [])
