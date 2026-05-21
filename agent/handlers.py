import asyncio
from datetime import datetime, UTC
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
        self._last_candle_epoch: float | None = None
        self._entry_candle_epoch: float | None = None

    async def get_market_analysis(self, symbol: str, timeframe: str, count: int = 60) -> dict:
        count = max(count, 60)  # EMA-50 + ADX-14 need at least 60 candles to stabilise
        candles = await market.get_candles(self.client, symbol, timeframe, count)
        if not candles:
            return {"error": "Sem candles retornados"}

        # Armazenar o epoch do último candle para cálculo da entrada
        if candles:
            self._last_candle_epoch = candles[-1]["time"]  # última posição = último candle
            # Calcular horário do próximo candle (próximo múltiplo de 60s)
            from datetime import datetime, UTC, timezone
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            # Encontrar o próximo múltiplo de 60s após o último candle
            last_candle_seconds = self._last_candle_epoch / 1000
            # Arredondar para cima até o próximo minuto completo
            seconds_in_minute = 60
            next_epoch_seconds = (
                (int(last_candle_seconds / seconds_in_minute) + 1) * seconds_in_minute
            )
            # Se já passou, ir para o próximo minuto
            while next_epoch_seconds < now_ms / 1000:
                next_epoch_seconds += seconds_in_minute

            self._entry_candle_epoch = next_epoch_seconds * 1000  # volta para ms
        else:
            self._last_candle_epoch = None
            self._entry_candle_epoch = None

        result = analyze(candles)
        result["symbol"] = symbol
        result["timeframe"] = timeframe
        self._last_analysis = result
        return result

    async def emit_signal(self, direction: str, confidence: float, reason: str = "") -> dict:
        """Emit a Rise/Fall/SEM_SINAL signal and schedule verification if not aborted."""
        # Calcular o horário exato de entrada
        if self._entry_candle_epoch is not None:
            from datetime import datetime, UTC, timezone
            entry_candle_time = datetime.fromtimestamp(self._entry_candle_epoch / 1000, tz=timezone.utc).isoformat()
            # Se já passou do horário de entrada, recalcular para o próximo candle
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            if self._entry_candle_epoch < now_ms:
                # Avançar para o próximo minuto
                self._entry_candle_epoch = int((self._entry_candle_epoch / 60000) + 1) * 60000
                entry_candle_time = datetime.fromtimestamp(self._entry_candle_epoch / 1000, tz=timezone.utc).isoformat()
        else:
            entry_candle_time = None

        quote_entry = await market.get_tick(self.client, self.config["symbol"]) if direction != "SEM_SINAL" else None

        signal = Signal(
            created_at=datetime.now(UTC).isoformat(),
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
            last_candle_epoch=self._last_candle_epoch,
            entry_candle_time=entry_candle_time,
        )

        signal_id = self.repo.insert(signal)

        if direction != "SEM_SINAL":
            asyncio.create_task(
                verifier.resolve(
                    self.client, self.repo, signal_id, quote_entry,
                    direction, self.config["symbol"], int(self.config["duration"]), entry_candle_time
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
