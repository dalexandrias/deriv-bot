import asyncio
import time
from datetime import datetime, timezone
from loguru import logger

from app.collector.deriv_client import TIMEFRAME_TO_GRANULARITY
from app.events.protocol import EventType
from app.events.publisher import publish
from app.signals.repository import SignalRepository


async def resolve(client, session_factory, signal_id, direction, symbol, timeframe,
                  entry_candle_time, settle_delay=2):
    try:
        granularity = TIMEFRAME_TO_GRANULARITY.get(timeframe)
        if not granularity:
            raise ValueError(f"Timeframe inválido '{timeframe}'")

        entry_dt = datetime.fromisoformat(entry_candle_time.replace('Z', '+00:00'))
        entry_epoch = int(entry_dt.timestamp())
        close_epoch = entry_epoch + granularity

        wait = close_epoch + settle_delay - time.time()
        if wait > 0:
            logger.info(f"Verifier #{signal_id}: aguardando {wait:.1f}s até candle fechar")
            await asyncio.sleep(wait)

        candle = await client.get_candle_by_epoch(symbol, granularity, entry_epoch)
        if candle is None:
            raise ValueError(f"Candle não encontrado (symbol={symbol}, epoch={entry_epoch})")

        entry_price = candle["open"]
        exit_price = candle["close"]

        outcome = "win" if (
            (direction == "CALL" and exit_price > entry_price) or
            (direction != "CALL" and exit_price < entry_price)
        ) else "loss"

        async with session_factory() as session:
            repo = SignalRepository(session)
            await repo.update_outcome(signal_id, entry_price, exit_price, outcome)
            await session.commit()

        delta = exit_price - entry_price
        delta_pct = (delta / entry_price) * 100
        icon = "✔" if outcome == "win" else "✘"
        logger.success(
            f"{icon} Resultado #{signal_id} | {direction} | {outcome.upper()} | "
            f"entry={entry_price} exit={exit_price} Δ={delta:+.3f} ({delta_pct:+.3f}%)"
        )
        publish(EventType.SIGNAL_RESOLVED, {
            "id": signal_id, "outcome": outcome.upper(),
            "status": "resolved",
            "entry_price": entry_price, "exit_price": exit_price,
        })

    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(f"Verifier #{signal_id} falhou: {e}")
        try:
            async with session_factory() as session:
                repo = SignalRepository(session)
                await repo.mark_error(signal_id)
                await session.commit()
        except Exception as db_err:
            logger.error(f"Verifier #{signal_id}: falha ao marcar erro no DB: {db_err}")
        publish(EventType.SIGNAL_RESOLVED, {
            "id": signal_id,
            "status": "error",
        })
