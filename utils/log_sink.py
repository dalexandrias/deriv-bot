"""Sink do loguru que publica cada log record como EventType.LOG no EventServer."""


def attach_event_sink() -> None:
    """Registra um sink no logger loguru que publica eventos LOG via publisher global.

    Deve ser chamado após set_event_server(). Usa enqueue=True para não bloquear.
    """
    from loguru import logger
    from events.protocol import EventType
    from events.publisher import publish

    def _sink(message) -> None:
        record = message.record
        publish(EventType.LOG, {
            "level": record["level"].name,
            "time": record["time"].strftime("%H:%M:%S"),
            "name": record["name"] or "",
            "message": record["message"],
        })

    logger.add(_sink, level="DEBUG", enqueue=True, format="{message}")
