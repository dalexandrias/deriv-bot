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
    resp = await client._send({"ticks": symbol})
    return float(resp["tick"]["quote"])


async def get_active_symbols(client: DerivClient) -> list[dict]:
    resp = await client._send({"active_symbols": "brief", "product_type": "basic"})
    return resp.get("active_symbols", [])
