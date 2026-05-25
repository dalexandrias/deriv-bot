from dataclasses import dataclass


@dataclass
class CycleCreate:
    cycle_number: int = 0
    symbol: str = "R_25"
    regime: str | None = None
    m15_bias: str | None = None
    time_window: str | None = None
    confluence_call: int = 0
    confluence_put: int = 0
    llm_direction: str = "NONE"
    llm_confidence: float = 0.0
    llm_rationale: str | None = None
    llm_raw_response: str | None = None
    emitted: bool = False
    signal_id: int | None = None
    skip_reason: str | None = None


@dataclass
class LessonCreate:
    content: str = ""
    topic: str = ""
    sample_size: int = 0
    confidence: float = 0.0
