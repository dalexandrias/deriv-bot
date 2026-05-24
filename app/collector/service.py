import asyncio
import time
from loguru import logger

from app.collector.deriv_client import DerivClient, TIMEFRAME_TO_GRANULARITY
from app.signals.repository import SignalRepository


class CollectorService:
    def __init__(self, client: DerivClient, repo: SignalRepository):
        self.client = client
        self.repo = repo
        self._running = False
        self._task: asyncio.Task | None = None
        self.symbols: list[str] = []
        self.timeframes: list[str] = []

    async def start(self, symbols: list[str], timeframes: list[str]) -> None:
        self.symbols = symbols
        self.timeframes = timeframes
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(f"Collector iniciado: symbols={symbols}, timeframes={timeframes}")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Collector parado")

    async def update_config(self, symbols: list[str], timeframes: list[str]) -> None:
        self.symbols = symbols
        self.timeframes = timeframes
        logger.info(f"Collector config atualizado: symbols={symbols}, timeframes={timeframes}")

    @property
    def is_running(self) -> bool:
        return self._running

    async def _loop(self) -> None:
        while self._running:
            try:
                await self.client.ensure_connected()
                for symbol in self.symbols:
                    for tf in self.timeframes:
                        try:
                            candles = await self.client.get_candles(symbol, tf, count=5)
                            await self.repo.upsert_candles(candles, symbol, tf)
                            await self.repo.session.commit()
                            logger.success(f"Candles salvas | {symbol}/{tf} | {len(candles)} candles | último epoch={candles[-1]['time'] if candles else '-'}")
                        except Exception as e:
                            logger.error(f"Erro ao coletar {symbol}/{tf}: {e}")
                            await self.repo.session.rollback()

                # Wait until next candle close
                granularity = TIMEFRAME_TO_GRANULARITY.get(self.timeframes[0] if self.timeframes else "5m", 300)
                now = time.time()
                next_close = (int(now / granularity) + 1) * granularity
                wait_secs = next_close - now
                await asyncio.sleep(wait_secs)
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error(f"Erro no collector loop: {e}")
                await asyncio.sleep(10)
