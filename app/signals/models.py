from dataclasses import dataclass


@dataclass
class SignalCreate:
    symbol: str = "R_25"
    timeframe: str = "5m"
    direction: str = "CALL"
    confidence: float = 0.5
    duration: int = 300
    status: str = "pending"
    rsi: float | None = None
    bb_position: float | None = None
    adx: float | None = None
    atr_pct: float | None = None
    price_vs_ema50: float | None = None
    macd_line: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    regime: str | None = None
    time_window: str | None = None
    m15_bias: str | None = None
    confluence_score: int | None = None
    strategy: str | None = None
    entry_candle_time: str | None = None
    reasoning: str | None = None
