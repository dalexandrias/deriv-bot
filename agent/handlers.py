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

    async def emit_signal(self, direction: str, confidence: float, reason: str = "") -> dict:
        """Emit a Rise/Fall/SEM_SINAL signal and schedule verification if not aborted."""
        quote_entry = await market.get_tick(self.client, self.config["symbol"]) if direction != "SEM_SINAL" else None

        signal = Signal(
            created_at=datetime.utcnow().isoformat(),
            symbol=self.config["symbol"],
            direction=direction,
            confidence=confidence,
            reason=reason,
            duration=int(self.config["duration"]),
            timeframe=self.config["timeframe"],
            rsi=self._last_analysis.get("rsi") if self._last_analysis else None,
            bb_position=self._last_analysis.get("bb_position") if self._last_analysis else None,
            adx=self._last_analysis.get("adx") if self._last_analysis else None,
            atr_pct=self._last_analysis.get("atr_pct") if self._last_analysis else None,
            price_vs_ema50=self._last_analysis.get("price_vs_ema50") if self._last_analysis else None,
            quote_entry=quote_entry,
            status="aborted" if direction == "SEM_SINAL" else "pending",
        )

        signal_id = self.repo.insert(signal)

        if direction != "SEM_SINAL":
            asyncio.create_task(
                verifier.resolve(
                    self.client, self.repo, signal_id, quote_entry,
                    direction, self.config["symbol"], int(self.config["duration"])
                )
            )

        status_str = "ABORTED" if direction == "SEM_SINAL" else "EMITTED"
        logger.info(
            f"SIGNAL #{signal_id} | {direction} | {status_str} | {self.config['symbol']} "
            f"| conf={confidence:.0%}" + (f" | {reason}" if reason else "")
        )
        return {"status": "signal_" + ("aborted" if direction == "SEM_SINAL" else "emitted"), "signal_id": signal_id, "direction": direction}

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
