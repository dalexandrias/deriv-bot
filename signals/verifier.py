import asyncio
import time
from signals.repository import SignalRepository
from deriv.client import DerivClient
from deriv import market
from deriv.market import TIMEFRAME_TO_GRANULARITY
from utils.logger import logger


async def resolve(
    client: DerivClient,
    repo: SignalRepository,
    signal_id: int,
    direction: str,
    symbol: str,
    timeframe: str,
    entry_candle_time: str,
    settle_delay: int = 2,
) -> None:
    """
    Waits for the entry candle to close, then validates WIN/LOSS
    using the candle's actual open and close prices.
    """
    try:
        from datetime import datetime, timezone

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

        candle = await market.get_candle_by_epoch(client, symbol, granularity, entry_epoch)
        if candle is None:
            logger.error(f"Verifier #{signal_id}: candle epoch={entry_epoch} não encontrado")
            return

        quote_entry = candle["open"]
        quote_exit = candle["close"]

        if direction == "CALL":
            outcome = "win" if quote_exit > quote_entry else "loss"
        else:
            outcome = "win" if quote_exit < quote_entry else "loss"

        repo.update_outcome(signal_id, quote_entry, quote_exit, outcome)
        logger.info(
            f"RESULT #{signal_id} | {direction} | {outcome.upper()} "
            f"| entry={quote_entry} exit={quote_exit}"
        )

    except asyncio.CancelledError:
        logger.info(f"Verifier #{signal_id} cancelado pelo sistema")
        raise
    except Exception as e:
        logger.error(f"Verifier #{signal_id} erro inesperado: {e}")
