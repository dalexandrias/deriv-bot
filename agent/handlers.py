import asyncio
from datetime import datetime
from deriv.client import DerivClient
from deriv import market, trading
from indicators.technical import analyze
from signals.repository import SignalRepository
from signals import verifier
from signals.models import Signal
from utils.logger import logger


class ToolHandlers:
    def __init__(self, client: DerivClient, config: dict, repo: SignalRepository):
        self.client = client
        self.config = config
        self.repo = repo
        self._last_analysis: dict | None = None

    async def get_market_analysis(self, symbol: str, timeframe: str, count: int = 20) -> dict:
        candles = await market.get_candles(self.client, symbol, timeframe, count)
        if not candles:
            return {"error": "Sem candles retornados"}
        result = analyze(candles)
        result["symbol"] = symbol
        result["timeframe"] = timeframe
        self._last_analysis = result
        return result

    async def emit_signal(self, direction: str, confidence: float, justification: str) -> dict:
        """Emit a Rise/Fall signal and schedule verification."""
        quote_entry = await market.get_tick(self.client, self.config["symbol"])

        signal = Signal(
            created_at=datetime.utcnow().isoformat(),
            symbol=self.config["symbol"],
            direction=direction,
            confidence=confidence,
            justification=justification,
            duration=int(self.config["duration"]),
            timeframe=self.config["timeframe"],
            rsi=self._last_analysis.get("rsi") if self._last_analysis else None,
            macd_signal=self._last_analysis.get("macd_signal") if self._last_analysis else None,
            trend=self._last_analysis.get("trend") if self._last_analysis else None,
            bb_position=self._last_analysis.get("bb_position") if self._last_analysis else None,
            quote_entry=quote_entry,
        )

        signal_id = self.repo.insert(signal)

        asyncio.create_task(
            verifier.resolve(
                self.client, self.repo, signal_id, quote_entry,
                direction, self.config["symbol"], int(self.config["duration"])
            )
        )

        logger.info(
            f"SIGNAL #{signal_id} | {direction} | {self.config['symbol']} "
            f"| entry={quote_entry} | dur={self.config['duration']}s "
            f"| conf={confidence:.0%} | {justification}"
        )
        return {"status": "signal_emitted", "signal_id": signal_id, "direction": direction}

    async def dispatch(self, name: str, args: dict) -> dict:
        fn = getattr(self, name, None)
        if fn is None:
            return {"error": f"Tool desconhecida: {name}"}
        try:
            return await fn(**args)
        except TypeError as e:
            return {"error": f"Argumentos inválidos para {name}: {e}"}
        except Exception as e:
            logger.exception(f"Erro ao executar tool {name}")
            return {"error": str(e)}
