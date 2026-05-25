from enum import Enum
from dataclasses import dataclass
from typing import Any
import json


class EventType(str, Enum):
    STATUS = "status"
    MARKET = "market"
    SIGNAL_EMITTED = "signal_emitted"
    SIGNAL_RESOLVED = "signal_resolved"
    LLM_RESPONSE = "llm_response"
    ERROR = "error"
    LOG = "log"
    CANDLE_SAVED = "candle_saved"
    CYCLE_LOGGED = "cycle_logged"
    LESSON_LEARNED = "lesson_learned"


@dataclass
class Event:
    type: EventType
    data: dict[str, Any]

    def to_json(self) -> str:
        return json.dumps({"type": self.type.value, "data": self.data}, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "Event":
        d = json.loads(json_str)
        return cls(type=EventType(d["type"]), data=d["data"])
