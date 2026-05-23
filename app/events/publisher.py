import asyncio
from typing import Any
from app.events.protocol import Event, EventType


class EventBus:
    """Simple in-process pub/sub for SSE and internal listeners."""

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        if q in self._subscribers:
            self._subscribers.remove(q)

    def publish(self, event_type: EventType, data: dict[str, Any]) -> None:
        event = Event(type=event_type, data=data)
        for q in self._subscribers:
            q.put_nowait(event)


_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def publish(event_type: EventType, data: dict[str, Any]) -> None:
    get_event_bus().publish(event_type, data)
