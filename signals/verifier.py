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
        # Validate duration
        if duration <= 0:
            logger.error(f"Invalid duration {duration} for signal #{signal_id}")
            return

        await asyncio.sleep(duration)

        # Fetch exit quote with validation
        try:
            quote_exit = await market.get_tick(client, symbol)
        except Exception as e:
            logger.error(f"Verifier #{signal_id} failed to fetch exit quote: {e}")
            return

        # Validate quote_exit
        if quote_exit is None:
            logger.error(f"Verifier #{signal_id}: No exit quote received (None)")
            return

        try:
            quote_exit_float = float(quote_exit)
        except (ValueError, TypeError) as e:
            logger.error(f"Verifier #{signal_id}: Invalid quote_exit type {type(quote_exit)}: {e}")
            return

        # Calculate outcome
        if direction == "CALL":
            outcome = "win" if quote_exit_float > quote_entry else "loss"
        else:  # PUT
            outcome = "win" if quote_exit_float < quote_entry else "loss"

        # Update repository
        try:
            repo.update_outcome(signal_id, quote_exit_float, outcome)
            logger.info(
                f"RESULT #{signal_id} | {direction} | {outcome.upper()} "
                f"| entry={quote_entry} exit={quote_exit_float}"
            )
        except Exception as db_error:
            logger.error(f"Verifier #{signal_id} failed to update outcome: {db_error}")
            return

    except asyncio.CancelledError:
        logger.info(f"Verifier #{signal_id} cancelled by system")
        raise
    except Exception as e:
        logger.error(f"Verifier #{signal_id} unexpected error: {e}")
