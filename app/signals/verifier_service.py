import asyncio
import time
from datetime import datetime, timezone
from loguru import logger

from app.collector.deriv_client import TIMEFRAME_TO_GRANULARITY
from app.events.protocol import EventType
from app.events.publisher import publish, get_event_bus
from app.signals.repository import SignalRepository


class VerifierService:
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self._running = False
        self._task: asyncio.Task | None = None
        self._event_queue: asyncio.Queue | None = None

    async def start(self) -> None:
        self._running = True
        self._event_queue = get_event_bus().subscribe()
        self._task = asyncio.create_task(self._loop())
        logger.info("VerifierService iniciado")

    async def stop(self) -> None:
        self._running = False
        if self._event_queue:
            get_event_bus().unsubscribe(self._event_queue)
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("VerifierService parado")

    @property
    def is_running(self) -> bool:
        return self._running

    async def _loop(self) -> None:
        while self._running:
            try:
                if not self._event_queue:
                    await asyncio.sleep(1)
                    continue

                event = await asyncio.wait_for(self._event_queue.get(), timeout=5.0)

                if event.type == EventType.CANDLE_SAVED:
                    await self._handle_candle_saved(event.data)

                await self._check_expired_signals()

            except asyncio.TimeoutError:
                await self._check_expired_signals()
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error(f"Erro no verifier loop: {e}")
                await asyncio.sleep(2)

    async def _handle_candle_saved(self, data: dict) -> None:
        symbol = data.get("symbol")
        timeframe = data.get("timeframe")
        epoch = data.get("epoch")
        candle_open = data.get("open")
        candle_close = data.get("close")

        if not all([symbol, timeframe, epoch is not None, candle_open is not None, candle_close is not None]):
            logger.warning(f"CANDLE_SAVED event malformado: {data}")
            return

        try:
            async with self.session_factory() as session:
                repo = SignalRepository(session)
                pending = await repo.get_pending_for_candle(symbol, timeframe, epoch)

                for sig in pending:
                    try:
                        outcome = self._calculate_outcome(sig.direction, candle_open, candle_close)
                        await repo.update_outcome(sig.id, candle_open, candle_close, outcome)
                        await session.commit()

                        delta = candle_close - candle_open
                        delta_pct = (delta / candle_open) * 100
                        icon = "✔" if outcome == "win" else "✘"
                        logger.success(
                            f"{icon} Resultado #{sig.id} | {sig.direction} | {outcome.upper()} | "
                            f"entry={candle_open} exit={candle_close} Δ={delta:+.3f} ({delta_pct:+.3f}%)"
                        )
                        publish(EventType.SIGNAL_RESOLVED, {
                            "id": sig.id,
                            "outcome": outcome.upper(),
                            "status": "resolved",
                            "entry_price": candle_open,
                            "exit_price": candle_close,
                        })
                    except Exception as e:
                        logger.error(f"Verifier falhou ao resolver sinal #{sig.id}: {e}")
                        try:
                            await repo.mark_error(sig.id)
                            await session.commit()
                        except Exception as db_err:
                            logger.error(f"Falha ao marcar sinal #{sig.id} como erro: {db_err}")
                        publish(EventType.SIGNAL_RESOLVED, {
                            "id": sig.id,
                            "status": "error",
                        })

                await self._catch_up_older_pending(repo, symbol, timeframe, epoch)

        except Exception as e:
            logger.error(f"Erro ao processar CANDLE_SAVED {symbol}/{timeframe} {epoch}: {e}")

    async def _catch_up_older_pending(
        self, repo: SignalRepository, symbol: str, timeframe: str, current_epoch: int
    ) -> None:
        pass

    async def _check_expired_signals(self) -> None:
        try:
            async with self.session_factory() as session:
                repo = SignalRepository(session)
                all_pending = await repo.get_all_pending()
                now = time.time()

                for sig in all_pending:
                    try:
                        deadline = self._calc_deadline(sig)
                        if deadline is None or now <= deadline:
                            continue
                        await repo.mark_error(sig.id)
                        await session.commit()
                        publish(EventType.SIGNAL_RESOLVED, {"id": sig.id, "status": "error"})
                        logger.warning(f"Sinal #{sig.id} expirado (deadline={deadline:.0f}) → marcado como erro")
                    except Exception as e:
                        logger.error(f"Erro ao marcar sinal #{sig.id} expirado: {e}")

        except Exception as e:
            logger.error(f"Erro ao verificar sinais expirados: {e}")

    @staticmethod
    def _calculate_outcome(direction: str, entry: float, exit: float) -> str:
        if direction == "CALL":
            return "win" if exit > entry else "loss"
        else:
            return "win" if exit < entry else "loss"

    @staticmethod
    def _calc_deadline(sig) -> float | None:
        """Candle close time + 2min buffer. Returns None if can't compute."""
        BUFFER = 120
        if sig.entry_candle_time:
            try:
                entry_epoch = int(
                    datetime.fromisoformat(sig.entry_candle_time.replace('Z', '+00:00')).timestamp()
                )
                granularity = TIMEFRAME_TO_GRANULARITY.get(sig.timeframe, 300)
                return entry_epoch + granularity + BUFFER
            except Exception:
                pass
        if sig.created_at and sig.duration:
            created_ts = sig.created_at.replace(tzinfo=timezone.utc).timestamp() if sig.created_at.tzinfo is None else sig.created_at.timestamp()
            granularity = TIMEFRAME_TO_GRANULARITY.get(sig.timeframe, 300)
            return created_ts + granularity + granularity + BUFFER
        return None
