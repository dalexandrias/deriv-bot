import asyncio
from signals.repository import SignalRepository
from deriv.client import DerivClient
from deriv import market
from utils.logger import logger

async def resolve(
    client: DerivClient,
    repo: SignalRepository,
    signal_id: int,
    quote_entry: float,
    direction: str,
    symbol: str,
    duration: int,
) -> None:
    """
    Async task that waits for signal duration, fetches exit price,
    determines outcome, and updates repository.
    """
    try:
        await asyncio.sleep(duration)
        quote_exit = await market.get_tick(client, symbol)

        if direction == "CALL":
            outcome = "win" if quote_exit > quote_entry else "loss"
        else:  # PUT
            outcome = "win" if quote_exit < quote_entry else "loss"

        repo.update_outcome(signal_id, quote_exit, outcome)
        logger.info(
            f"RESULT #{signal_id} | {direction} | {outcome.upper()} "
            f"| entry={quote_entry} exit={quote_exit}"
        )
    except Exception as e:
        logger.error(f"Verifier #{signal_id} failed: {e}")
