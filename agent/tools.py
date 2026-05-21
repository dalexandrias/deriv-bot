TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_market_analysis",
            "description": "Busca candles recentes e retorna análise técnica: RSI, Bollinger Bands, EMA-50, ADX-14 (força da tendência), ATR-14 (volatilidade)",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol":    {"type": "string", "description": "Ex: frxEURUSD, R_100"},
                    "timeframe": {"type": "string", "enum": ["1m", "5m", "15m", "1h"]},
                    "count":     {"type": "integer", "default": 60, "minimum": 60, "description": "Mínimo 60 — necessário para EMA-50 e ADX-14 estabilizarem"},
                },
                "required": ["symbol", "timeframe"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "emit_signal",
            "description": "Emits a Rise (CALL), Fall (PUT), or NO_SIGNAL (SEM_SINAL) decision. Confidence should reflect real perceived probability.",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction":  {"type": "string", "enum": ["CALL", "PUT", "SEM_SINAL"]},
                    "confidence": {"type": "number", "description": "0.0–1.0; must reflect real perceived probability. Never 1.0."},
                    "reason":     {"type": "string", "description": "Optional one-line reason for audit only; not processed by logic"},
                },
                "required": ["direction", "confidence"],
            },
        },
    },
]
