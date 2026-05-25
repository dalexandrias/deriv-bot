import asyncio
import time
from loguru import logger
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.collector.deriv_client import DerivClient, TIMEFRAME_TO_GRANULARITY
from app.events.protocol import EventType
from app.events.publisher import publish
from app.signals.repository import SignalRepository


class CollectorService:
    def __init__(self, client: DerivClient, session_factory: async_sessionmaker):
        self.client = client
        self.session_factory = session_factory
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

    SETTLE_DELAY = 3  # seconds after candle close before reading price

    async def _loop(self) -> None:
        while self._running:
            try:
                await self.client.ensure_connected()
                now = time.time()
                async with self.session_factory() as session:
                    repo = SignalRepository(session)
                    for symbol in self.symbols:
                        for tf in self.timeframes:
                            try:
                                candles = await self.client.get_candles(symbol, tf, count=5)
                                await repo.upsert_candles(candles, symbol, tf)
                                await session.commit()
                                logger.success(f"Candles salvas | {symbol}/{tf} | {len(candles)} candles | último epoch={candles[-1]['time'] if candles else '-'}")

                                granularity = TIMEFRAME_TO_GRANULARITY.get(tf, 300)
                                for c in candles:
                                    epoch = c["time"]
                                    # Only publish if candle closed at least SETTLE_DELAY seconds ago
                                    if (epoch + granularity + self.SETTLE_DELAY) <= now:
                                        publish(EventType.CANDLE_SAVED, {
                                            "symbol": symbol,
                                            "timeframe": tf,
                                            "epoch": epoch,
                                            "open": c["open"],
                                            "high": c["high"],
                                            "low": c["low"],
                                            "close": c["close"],
                                        })
                            except Exception as e:
                                logger.error(f"Erro ao coletar {symbol}/{tf}: {e}")
                                await session.rollback()

                # Wait until next candle close + settle
                granularity = TIMEFRAME_TO_GRANULARITY.get(self.timeframes[0] if self.timeframes else "5m", 300)
                now = time.time()
                next_close = (int(now / granularity) + 1) * granularity
                wait_secs = next_close - now + self.SETTLE_DELAY
                await asyncio.sleep(wait_secs)
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error(f"Erro no collector loop: {e}")
                await asyncio.sleep(10)
