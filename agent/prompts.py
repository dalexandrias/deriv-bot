SYSTEM_PROMPT_TEMPLATE = """Você é um agente analista de mercado operando no Volatility 100 Index (R_100) na plataforma Deriv.

## Contexto crítico
R_100 é um índice de volatilidade constante (~100% anual) com zero drift — gerado por um algoritmo criptograficamente seguro de números aleatórios. Nenhum padrão histórico garante o próximo tick. Você deve declarar honestamente sua **confiança real** na decisão, sabendo que será avaliada posteriormente contra o resultado efetivo (win_rate vs confidence declarada).

## Seu processo:
Analise os indicadores técnicos fornecidos e o bloco de aprendizado (histórico de win/loss por padrão), então retorne sua decisão em formato JSON.

## Formato de resposta OBRIGATÓRIO:
Retorne APENAS um JSON válido no formato:
```json
{
  "confidence": 0.62,
  "direction": "CALL" | "PUT" | "NONE"
}
```

Onde:
- **confidence**: número de 0.0 a 1.0 refletindo sua probabilidade percebida (nunca 1.0)
- **direction**: "CALL" (Rise), "PUT" (Fall), ou "NONE" (sem sinal)

## Importante:
- Sua confiança deve refletir a probabilidade real da previsão estar correta
- Use valores baixos (0.50-0.55) quando indicadores não convergem claramente
- Consulte o bloco de aprendizado — padrões com win_rate ≥60% são favoráveis; <40% desfavoráveis
- Padrões com poucos exemplos (<5) têm baixíssima significância estatística — trate com ceticismo
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
    last_close = indicators.get("last_close", 0)
    rsi = indicators.get("rsi", float("nan"))
    rsi_prev3 = indicators.get("rsi_prev3", [])
    close_prev5 = indicators.get("close_prev5", [])
    bb_position = indicators.get("bb_position", "N/A")
    bb_upper = indicators.get("bb_upper", 0)
    bb_lower = indicators.get("bb_lower", 0)
    bb_dist_upper_atr = indicators.get("bb_dist_upper_atr", 0)
    bb_dist_lower_atr = indicators.get("bb_dist_lower_atr", 0)
    ema50 = indicators.get("ema50", 0)
    ema50_dist_atr = indicators.get("ema50_dist_atr", 0)
    adx = indicators.get("adx", float("nan"))
    atr_pct = indicators.get("atr_pct", 0)

    # RSI trajectory
    rsi_traj_str = ""
    if len(rsi_prev3) >= 2:
        traj = " → ".join(f"{r:.1f}" for r in rsi_prev3)
        if rsi_prev3[-1] > rsi_prev3[0]:
            rsi_dir = "subindo"
        elif rsi_prev3[-1] < rsi_prev3[0]:
            rsi_dir = "caindo"
        else:
            rsi_dir = "estável"
        rsi_traj_str = f"\n  Trajetória 3 candles: [{traj}] ({rsi_dir})"

    # Recent closes with price change
    close_line = ""
    if close_prev5:
        closes_str = ", ".join(f"{c:.2f}" for c in close_prev5)
        if len(close_prev5) >= 2 and close_prev5[0] != 0:
            price_change_pct = (close_prev5[-1] - close_prev5[0]) / close_prev5[0] * 100
            sign = "+" if price_change_pct >= 0 else ""
            close_line = f"Últimos 5 closes: [{closes_str}] (variação: {sign}{price_change_pct:.2f}%)"
        else:
            close_line = f"Últimos 5 closes: [{closes_str}]"

    # EMA direction
    ema_dir = "acima" if ema50_dist_atr >= 0 else "abaixo"
    ema_sign = "+" if ema50_dist_atr >= 0 else ""

    close_block = f"{close_line}\n" if close_line else ""

    indicators_section = (
        f"\n## Indicadores Técnicos\n"
        f"Preço atual: {last_close:.5f}\n"
        f"{close_block}\n"
        f"RSI-14: {rsi:.1f} (sobrecompra >70, sobrevenda <30){rsi_traj_str}\n\n"
        f"Bollinger(20,2): preço {bb_position} da banda\n"
        f"  Upper: {bb_upper:.5f} ({bb_dist_upper_atr:.2f} ATRs acima do preço)\n"
        f"  Lower: {bb_lower:.5f} ({bb_dist_lower_atr:.2f} ATRs abaixo do preço)\n\n"
        f"EMA-50: {ema50:.5f} | Preço {ema_sign}{ema50_dist_atr:.2f} ATRs {ema_dir}\n"
        f"ADX-14: {adx:.1f} (força: <25 fraco, 25-50 moderado, >50 forte)\n"
        f"ATR-14: {atr_pct:.2f}% (volatilidade por candle)\n"
    )

    timing_section = ""
    if last_candle_time and next_entry_time:
        timing_section = (
            f"\n## Contexto Temporal\n"
            f"- Último candle analisado: {last_candle_time}\n"
            f"- Próximo candle de entrada: {next_entry_time}\n"
            f"- Escala: indicadores calculados em candles de {config['timeframe']}, "
            f"sinal expira em {config['duration']}s — prefira convergência de múltiplos indicadores.\n"
        )

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
