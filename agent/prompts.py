SYSTEM_PROMPT_TEMPLATE = """Você é um agente analista de mercado operando no Volatility 100 Index (R_100) na plataforma Deriv.

## Contexto crítico
R_100 é um índice de volatilidade constante (~100% anual) com zero drift — gerado por um algoritmo criptograficamente seguro de números aleatórios. Nenhum padrão histórico garante o próximo tick. Você deve declarar honestamente sua **confiança real** na decisão, sabendo que será avaliada posteriormente contra o resultado efetivo (win_rate vs confidence declarada).

## Seu processo:
Analise os indicadores técnicos fornecidos e o bloco de aprendizado (histórico de win/loss por padrão), entao retorne sua decisão em formato JSON.

## Formato de resposta OBRIGATÓRIO:
Retorne APENAS um JSON válido no formato:
```json
{{
  "confidence": 0.XX,
  "direction": "CALL" | "PUT" | "NONE"
}}
```

Onde:
- **confidence**: número de 0.0 a 1.0 refletindo sua probabilidade percebida (nunca 1.0)
- **direction**: "CALL" (Rise), "PUT" (Fall), ou "NONE" (sem sinal)

## Importante:
- Sua confiança deve refletir a probabilidade real da previsão estar correta
- Use valores baixos (0.50-0.55) quando indicadores não convergem claramente
- Consulte o bloco de aprendizado — padrões com win_rate ≥60% são favoráveis; <40% desfavoráveis
- Não há regras hardcoded; você interpreta os dados e decide
- Retorne APENAS o JSON, sem texto adicional
"""


def build_system_prompt(config: dict) -> str:
    return SYSTEM_PROMPT_TEMPLATE


def build_user_context(
    config: dict,
    indicators: dict,
    learning_block: str = "",
    last_candle_time: str = "",
    next_entry_time: str = "",
) -> str:
    """Build user context with indicators already calculated."""

    # Format indicators for prompt
    indicators_section = f"""
## Indicadores Técnicos
- RSI-14: {indicators.get("rsi", "N/A"):.1f} (sobrecompra >70, sobrevenda <30)
- Bollinger Bands: preço em {indicators.get("bb_position", "N/A")} da banda (100=no meio)
- ADX-14: {indicators.get("adx", "N/A"):.1f} (força de tendência: <25 fraco, >50 forte)
- ATR-14: {indicators.get("atr_pct", "N/A"):.1f}% (volatilidade)
- EMA-50: preço {indicators.get("price_vs_ema50", "N/A")} de {indicators.get("ema50", "N/A"):.2f}
"""

    # Add timing context if available
    timing_section = ""
    if last_candle_time and next_entry_time:
        timing_section = f"""
## Contexto Temporal
- Último candle analisado: {last_candle_time}
- Próximo candle de entrada: {next_entry_time}
"""

    # Build learning block
    learning_section = (
        f"\n## Histórico de Aprendizado\n{learning_block}" if learning_block else ""
    )

    return (
        f"Análise de mercado iniciada.\n"
        f"Ativo: {config['symbol']}\n"
        f"Timeframe: {config['timeframe']}\n"
        f"Duração do sinal: {config['duration']}s\n"
        f"{indicators_section}"
        f"{timing_section}"
        f"{learning_section}\n"
        "Analise os indicadores acima e retorne sua decisão em JSON."
    )
