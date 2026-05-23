"""Módulo de eventos para comunicação bot → UI."""
from events.server import EventServer
from events.protocol import Event, EventType
from events.publisher import publish, set_event_server

__all__ = ["EventServer", "Event", "EventType", "publish", "set_event_server"]
