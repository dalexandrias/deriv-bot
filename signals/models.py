from dataclasses import dataclass, field
from datetime import datetime, UTC

@dataclass
class Signal:
    """Represents a Rise/Fall signal emitted by the agent."""
    id: int | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    symbol: str = "R_100"
    direction: str = "CALL"  # "CALL" | "PUT"
    confidence: float = 0.5  # 0.0–1.0
    justification: str = ""
    duration: int = 5  # seconds
    timeframe: str = "1m"
    rsi: float | None = None
    macd_signal: str | None = None  # "compra" | "venda"
    trend: str | None = None  # "alta" | "baixa" | "lateral"
    bb_position: str | None = None
    quote_entry: float | None = None
    quote_exit: float | None = None
    outcome: str | None = None  # "win" | "loss"
    status: str = "pending"  # "pending" | "resolved" | "aborted"


@dataclass
class Outcome:
    """Result of a resolved Rise/Fall signal."""
    signal_id: int
    quote_exit: float
    outcome: str  # "win" | "loss"
