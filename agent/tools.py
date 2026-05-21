TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_market_analysis",
            "description": "Busca candles recentes e retorna análise técnica completa com RSI, MACD e Bollinger Bands",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol":    {"type": "string", "description": "Ex: frxEURUSD, R_100"},
                    "timeframe": {"type": "string", "enum": ["1m", "5m", "15m", "1h"]},
                    "count":     {"type": "integer", "default": 20},
                },
                "required": ["symbol", "timeframe"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "emit_signal",
            "description": "Emits a Rise (CALL) or Fall (PUT) signal for R_100. Use when indicators are aligned.",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction":     {"type": "string", "enum": ["CALL", "PUT"]},
                    "confidence":    {"type": "number", "description": "Confidence 0.0–1.0"},
                    "justification": {"type": "string", "description": "Reason based on indicators"},
                },
                "required": ["direction", "confidence", "justification"],
            },
        },
    },
]
