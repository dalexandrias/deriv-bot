import asyncio

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.api import bot, collector, signals, indicators, health

router = APIRouter(prefix="/api/v1")
router.include_router(bot.router)
router.include_router(collector.router)
router.include_router(signals.router)
router.include_router(indicators.router)
router.include_router(health.router)


@router.get("/events/stream")
async def event_stream():
    from app.events.publisher import get_event_bus
    bus = get_event_bus()
    queue = bus.subscribe()

    async def generate():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=25.0)
                    yield {"data": event.to_json()}
                except asyncio.TimeoutError:
                    yield {"comment": "keepalive"}
        except asyncio.CancelledError:
            bus.unsubscribe(queue)

    return EventSourceResponse(generate())
