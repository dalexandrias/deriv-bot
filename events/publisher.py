"""Helper simplificado para publicar eventos no EventServer."""
from typing import Any
from events.protocol import Event, EventType


# Referência global para o EventServer (definido no main.py)
_event_server = None


def set_event_server(server) -> None:
    """Define a referência global do EventServer."""
    global _event_server
    _event_server = server


def publish(event_type: EventType, data: dict[str, Any]) -> None:
    """Publica um evento no EventServer."""
    if _event_server is None:
        return

    event = Event(type=event_type, data=data)
    # Usar create_task para não bloquear
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(_event_server.broadcast(event))
        else:
            # Se não está rodando (ex: durante testes), ignorar
            pass
    except RuntimeError:
        # Não há event loop rodando
        pass
