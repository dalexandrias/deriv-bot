"""Protocolo de eventos para comunicação bot → UI via Unix socket."""
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Any


class EventType(str, Enum):
    """Tipos de eventos que o bot pode enviar."""
    STATUS = "status"
    MARKET = "market"
    SIGNAL_EMITTED = "signal_emitted"
    SIGNAL_RESOLVED = "signal_resolved"
    LLM_RESPONSE = "llm_response"
    ERROR = "error"
    LOG = "log"


@dataclass
class Event:
    """Mensagem de evento enviada pelo socket."""
    type: EventType
    data: dict[str, Any]

    def to_json(self) -> str:
        """Converte para JSON string."""
        import json
        return json.dumps({"type": self.type.value, "data": self.data}, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "Event":
        """Cria Event a partir de JSON string."""
        import json
        d = json.loads(json_str)
        return cls(type=EventType(d["type"]), data=d["data"])


# Tipos específicos de eventos (para type checking)
@dataclass
class StatusEvent:
    """Evento de mudança de status do bot."""
    status: str  # "connecting", "connected", "waiting", "analyzing", "signal_emitted", "error", "idle"
    detail: str = ""


@dataclass
class MarketEvent:
    """Evento com dados de mercado atualizados."""
    m5_indicators: dict
    m15_indicators: dict
    pre_analysis: dict
    last_candle_time: str
    next_entry_time: str


@dataclass
class SignalEmittedEvent:
    """Evento de novo sinal emitido."""
    id: int
    direction: str  # "CALL" or "PUT"
    confidence: float
    symbol: str
    regime: str
    time_window: str
    strategy: str
    entry_candle_time: str


@dataclass
class SignalResolvedEvent:
    """Evento de sinal resolvido (WIN/LOSS)."""
    id: int
    outcome: str  # "win" or "loss"
    quote_entry: float
    quote_exit: float


@dataclass
class LLMResponseEvent:
    """Evento com resposta do LLM."""
    direction: str
    confidence: float
    raw_response: str


@dataclass
class ErrorEvent:
    """Evento de erro."""
    message: str
    detail: str = ""


@dataclass
class LogEvent:
    """Evento de log do bot (capturado via sink do loguru)."""
    level: str   # "DEBUG", "INFO", "WARNING", "ERROR"
    time: str    # HH:MM:SS
    name: str    # nome do módulo/logger
    message: str
