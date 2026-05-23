import asyncio
import time
from datetime import datetime, timezone
from loguru import logger

from app.collector.deriv_client import TIMEFRAME_TO_GRANULARITY
from app.events.protocol import EventType
from app.events.publisher import publish


async def resolve(client, repo, signal_id, direction, symbol, timeframe,
                  entry_candle_time, settle_delay=2):
    try:
        granularity = TIMEFRAME_TO_GRANULARITY.get(timeframe)
        if not granularity:
            logger.error(f"Verifier #{signal_id}: timeframe inválido '{timeframe}'")
            return

        entry_dt = datetime.fromisoformat(entry_candle_time.replace('Z', '+00:00'))
        entry_epoch = int(entry_dt.timestamp())
        close_epoch = entry_epoch + granularity

        wait = close_epoch + settle_delay - time.time()
        if wait > 0:
            logger.info(f"Verifier #{signal_id}: aguardando {wait:.1f}s até candle fechar")
            await asyncio.sleep(wait)

        candle = await client.get_candle_by_epoch(symbol, granularity, entry_epoch)
        if candle is None:
            logger.error(f"Verifier #{signal_id}: candle não encontrado")
            return

        entry_price = candle["open"]
        exit_price = candle["close"]

        outcome = "win" if (
            (direction == "CALL" and exit_price > entry_price) or
            (direction != "CALL" and exit_price < entry_price)
        ) else "loss"

        await repo.update_outcome(signal_id, entry_price, exit_price, outcome)
        await repo.session.commit()
        logger.info(f"RESULT #{signal_id} | {direction} | {outcome.upper()} | entry={entry_price} exit={exit_price}")
        publish(EventType.SIGNAL_RESOLVED, {
            "id": signal_id, "outcome": outcome,
            "quote_entry": entry_price, "quote_exit": exit_price,
        })
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(f"Verifier #{signal_id} erro: {e}")
