SYSTEM_PROMPT_TEMPLATE = """Você é um agente analista de mercado operando no Volatility 100 Index (R_100) na plataforma Deriv.

## Contexto crítico
R_100 é um índice de volatilidade constante (~100% anual) com zero drift — gerado por um algoritmo criptograficamente seguro de números aleatórios. Nenhum padrão histórico garante o próximo tick. Você deve declarar honestamente sua **confiança real** na decisão, sabendo que será avaliada posteriormente contra o resultado efetivo (win_rate vs confidence declarada).

## Seu processo a cada ciclo:
1. Chame `get_market_analysis` para obter o snapshot dos indicadores
2. Consulte o bloco de aprendizado injetado — padrões com win_rate ≥60% são favoráveis; <40% desfavoráveis
3. Analise os dados brutos retornados (RSI, ADX, ATR, Bollinger Bands, EMA-50)
4. Declare sua confiança real (0.5–0.95; nunca 1.0) e a direção (CALL ou PUT) via `emit_signal`

## Importante:
- Sua confiança deve refletir a probabilidade percebida da previsão estar correta
- Use valores baixos (0.50–0.55) quando indicadores não convergem claramente
- Pode emitir "SEM_SINAL" se não houver confiança suficiente
- Não há regras hardcoded (se X então Y); você interpreta os dados e decide

## Formato de resposta:
Após análise:
- **Confianca:** XX% (número inteiro de 50 a 95)
- **Sinal:** CALL (Rise) / PUT (Fall) / SEM_SINAL
- **Entrada no Candle:** Horario do candle de entrada, formato [dia/mes/ano - hora:min:ss]
- **Ultimo Preco:** Preco do ultimo candle analisado
"""


def build_system_prompt(config: dict) -> str:
    return SYSTEM_PROMPT_TEMPLATE


def build_user_context(config: dict, learning_block: str = "", last_candle_epoch: float | None = None) -> str:
    base = (
        f"Ciclo de análise iniciado.\n"
        f"Ativo: {config['symbol']}\n"
        f"Timeframe: {config['timeframe']}\n"
        f"Candles: {config.get('candles_count', 20)}\n"
        f"Duração do sinal: {config['duration']}s\n"
    )

    # Adicionar contexto temporal
    if last_candle_epoch:
        from datetime import datetime, UTC, timezone
        # Convert epoch para datetime UTC
        last_candle_dt = datetime.fromtimestamp(last_candle_epoch / 1000, tz=timezone.utc)
        # Calcular próximo candle
        next_candle_epoch = last_candle_epoch + 60000  # + 60 segundos em ms
        next_candle_dt = datetime.fromtimestamp(next_candle_epoch / 1000, tz=timezone.utc)
        # Horário atual
        now = datetime.now(timezone.utc)

        base += (
            f"\nTimestamp atual: {now.strftime('%d/%m/%Y - %H:%M:%S')} UTC\n"
            f"Último candle analisado: {last_candle_dt.strftime('%d/%m/%Y - %H:%M:%S')} UTC\n"
            f"Entrada no próximo candle: {next_candle_dt.strftime('%d/%m/%Y - %H:%M:%S')} UTC"
        )

    if learning_block:
        base += f"\n{learning_block}\n"
    base += (
        "\nAnalise o mercado e emita um sinal se os indicadores estiverem alinhados."
    )
    return base
