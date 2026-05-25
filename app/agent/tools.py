from app.indicators.technical import analyze
from app.signals.repository import SignalRepository

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_signal_history",
            "description": (
                "Consulta sinais de trading resolvidos (wins e losses) gravados no banco de dados. "
                "Use para entender padrões históricos de acerto/erro, como o bot se comportou em "
                "condições parecidas com a atual, e calibrar a confiança do sinal atual. "
                "Retorna lista de sinais com direção, confiança, indicadores e resultado (win/loss)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Quantidade máxima de sinais a retornar (padrão 10, máximo 50).",
                        "default": 10,
                    },
                    "outcome": {
                        "type": "string",
                        "enum": ["win", "loss", "any"],
                        "description": "Filtrar por resultado. Use 'any' para ver todos.",
                        "default": "any",
                    },
                    "direction": {
                        "type": "string",
                        "enum": ["CALL", "PUT", "any"],
                        "description": "Filtrar por direção do sinal. Use 'any' para ver todos.",
                        "default": "any",
                    },
                    "recent_days": {
                        "type": "integer",
                        "description": "Se informado, retorna apenas sinais dos últimos N dias.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_candles_range",
            "description": (
                "Retorna candles OHLC históricos do banco de dados local. "
                "Use para inspecionar price action passado, identificar suportes e resistências, "
                "ou obter dados de entrada para a tool calc_indicator com parâmetros customizados. "
                "Os candles são retornados em ordem cronológica crescente. "
                "Suporta timeframes 5m (decisão) e 15m (contexto de tendência)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Quantidade de candles a retornar (padrão 60, máximo 500).",
                        "default": 60,
                    },
                    "before_epoch": {
                        "type": "integer",
                        "description": "Se informado, retorna candles com epoch menor que este valor (Unix timestamp em segundos). Útil para janelas históricas específicas.",
                    },
                    "timeframe": {
                        "type": "string",
                        "enum": ["5m", "15m"],
                        "description": "Timeframe dos candles (padrão: 5m). Use '15m' para contexto de tendência M15.",
                        "default": "5m",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calc_indicator",
            "description": (
                "Recalcula um indicador técnico com parâmetros customizados sobre candles históricos. "
                "Use para testar se uma janela diferente (ex: RSI-7 em vez de RSI-14) teria gerado "
                "um sinal mais claro, ou para fazer backtesting rápido de uma configuração alternativa. "
                "Os candles são buscados automaticamente do banco de dados. Suporta timeframes 5m e 15m."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "enum": ["rsi", "bb", "ema", "macd", "adx", "atr"],
                        "description": "Nome do indicador a calcular.",
                    },
                    "params": {
                        "type": "object",
                        "description": (
                            "Parâmetros específicos do indicador. "
                            "RSI: {period}. "
                            "BB: {period, std_dev}. "
                            "EMA: {period}. "
                            "MACD: {fast, slow, signal}. "
                            "ADX: {period}. "
                            "ATR: {period}."
                        ),
                    },
                    "count": {
                        "type": "integer",
                        "description": "Quantos candles históricos usar como entrada (padrão 60).",
                        "default": 60,
                    },
                    "before_epoch": {
                        "type": "integer",
                        "description": "Se informado, usa candles antes deste epoch. Útil para simular análises passadas.",
                    },
                    "timeframe": {
                        "type": "string",
                        "enum": ["5m", "15m"],
                        "description": "Timeframe dos candles (padrão: 5m). Use '15m' para contexto de tendência M15.",
                        "default": "5m",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "emit_signal",
            "description": (
                "Emite a decisão final da análise. Chame esta tool EXATAMENTE UMA VEZ por ciclo, "
                "ao final de sua análise. Use AGUARDE quando: regime indefinido + janela ruim SEM confluência, "
                "OU conflito forte M5×M15 sem confirmação adicional. Caso contrário, sempre escolha COMPRA ou VENDA "
                "com confiança ajustada à força da confluência."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "enum": ["COMPRA", "VENDA", "AGUARDE"],
                        "description": "Direção do sinal: COMPRA, VENDA ou AGUARDE.",
                    },
                    "confidence": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                        "description": "Nível de confiança 0-100. Use 0 para AGUARDE.",
                    },
                    "entry_time": {
                        "type": "string",
                        "description": "Horário do próximo candle M5 a operar, formato HH:MM. Obrigatório para COMPRA/VENDA, opcional para AGUARDE.",
                    },
                    "rationale": {
                        "type": "string",
                        "description": "Justificativa curta (1-2 frases) para a decisão.",
                    },
                },
                "required": ["direction", "confidence"],
            },
        },
    },
]


class ToolDispatcher:
    """Executes tool calls requested by the LLM."""

    def __init__(self, repo: SignalRepository, symbol: str, decision_timeframe: str, context_timeframe: str):
        self.repo = repo
        self.symbol = symbol
        self.decision_timeframe = decision_timeframe
        self.context_timeframe = context_timeframe
        self.emitted_signal: dict | None = None

    async def dispatch(self, name: str, args: dict) -> dict:
        if name == "query_signal_history":
            return await self._query_signal_history(**args)
        if name == "get_candles_range":
            return await self._get_candles_range(**args)
        if name == "calc_indicator":
            return await self._calc_indicator(**args)
        if name == "emit_signal":
            return await self._emit_signal(**args)
        return {"error": f"Tool desconhecida: {name}"}

    async def _query_signal_history(
        self,
        limit: int = 10,
        outcome: str = "any",
        direction: str = "any",
        recent_days: int | None = None,
    ) -> dict:
        signals = await self.repo.get_signals_filtered(
            limit=limit, outcome=outcome, direction=direction, recent_days=recent_days
        )
        return {"count": len(signals), "signals": signals}

    async def _get_candles_range(
        self, count: int = 60, before_epoch: int | None = None, timeframe: str = "5m"
    ) -> dict:
        count = min(count, 500)
        if timeframe not in ("5m", "15m"):
            timeframe = self.decision_timeframe
        candles = await self.repo.get_candles_range(
            self.symbol, timeframe, count=count, before_epoch=before_epoch
        )
        return {"count": len(candles), "candles": candles, "timeframe": timeframe}

    async def _calc_indicator(
        self,
        name: str,
        params: dict | None = None,
        count: int = 60,
        before_epoch: int | None = None,
        timeframe: str = "5m",
    ) -> dict:
        params = params or {}
        count = min(max(count, 30), 500)
        if timeframe not in ("5m", "15m"):
            timeframe = self.decision_timeframe
        candles = await self.repo.get_candles_range(
            self.symbol, timeframe, count=count, before_epoch=before_epoch
        )
        if len(candles) < 14:
            return {"error": "Candles insuficientes no banco para calcular o indicador."}

        import pandas as pd
        from ta.momentum import RSIIndicator
        from ta.trend import EMAIndicator, ADXIndicator, MACD
        from ta.volatility import BollingerBands, AverageTrueRange

        df = pd.DataFrame(candles)
        for col in ("open", "high", "low", "close"):
            df.loc[:, col] = df[col].astype(float)
        close = df["close"]

        try:
            if name == "rsi":
                period = int(params.get("period", 14))
                series = RSIIndicator(close=close, window=period).rsi()
                val = float(series.dropna().iloc[-1])
                return {"indicator": "rsi", "period": period, "value": round(val, 2)}

            if name == "bb":
                period = int(params.get("period", 20))
                std_dev = float(params.get("std_dev", 2.0))
                bb = BollingerBands(close=close, window=period, window_dev=std_dev)
                upper = float(bb.bollinger_hband().iloc[-1])
                lower = float(bb.bollinger_lband().iloc[-1])
                last = float(close.iloc[-1])
                position = "acima" if last > upper else ("abaixo" if last < lower else "dentro")
                return {
                    "indicator": "bb", "period": period, "std_dev": std_dev,
                    "upper": round(upper, 5), "lower": round(lower, 5),
                    "last_close": round(last, 5), "position": position,
                }

            if name == "ema":
                period = int(params.get("period", 50))
                series = EMAIndicator(close=close, window=period).ema_indicator()
                val = float(series.dropna().iloc[-1])
                last = float(close.iloc[-1])
                return {
                    "indicator": "ema", "period": period,
                    "value": round(val, 5), "last_close": round(last, 5),
                    "price_vs_ema": "acima" if last > val else "abaixo",
                }

            if name == "macd":
                fast = int(params.get("fast", 12))
                slow = int(params.get("slow", 26))
                signal = int(params.get("signal", 9))
                obj = MACD(close=close, window_fast=fast, window_slow=slow, window_sign=signal)
                return {
                    "indicator": "macd", "fast": fast, "slow": slow, "signal": signal,
                    "macd_line": round(float(obj.macd().dropna().iloc[-1]), 5),
                    "macd_signal": round(float(obj.macd_signal().dropna().iloc[-1]), 5),
                    "macd_histogram": round(float(obj.macd_diff().dropna().iloc[-1]), 5),
                }

            if name == "adx":
                period = int(params.get("period", 14))
                series = ADXIndicator(high=df["high"], low=df["low"], close=close, window=period).adx()
                val = float(series.dropna().iloc[-1])
                return {"indicator": "adx", "period": period, "value": round(val, 2)}

            if name == "atr":
                period = int(params.get("period", 14))
                series = AverageTrueRange(high=df["high"], low=df["low"], close=close, window=period).average_true_range()
                val = float(series.dropna().iloc[-1])
                last = float(close.iloc[-1])
                return {
                    "indicator": "atr", "period": period,
                    "value": round(val, 5),
                    "pct": round(val / last * 100, 2) if last else 0.0,
                }

            return {"error": f"Indicador não suportado: {name}"}

        except Exception as e:
            return {"error": str(e)}

    async def _emit_signal(
        self,
        direction: str,
        confidence: int,
        entry_time: str | None = None,
        rationale: str = "",
    ) -> dict:
        direction_map = {"COMPRA": "CALL", "VENDA": "PUT", "AGUARDE": "WAIT"}
        mapped_direction = direction_map.get(direction.upper())
        if not mapped_direction:
            return {"error": f"Direção inválida: {direction}. Use COMPRA, VENDA ou AGUARDE."}
        if not 0 <= confidence <= 100:
            return {"error": f"Confiança deve estar entre 0 e 100, recebido: {confidence}"}
        self.emitted_signal = {
            "direction": mapped_direction,
            "confidence": confidence / 100.0,
            "entry_time": entry_time or "",
            "rationale": rationale,
            "raw": "tool",
        }
        return {"ok": True, "received": self.emitted_signal}
