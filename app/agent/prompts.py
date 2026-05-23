"""Prompts for the Deriv trading bot agent.

System prompt and user context builder for the LLM.
Uses the new dual-timeframe (M5 + M15) approach with programmatic pre-analysis.
"""

SYSTEM_PROMPT_TEMPLATE = """Você é um especialista trader em Volatility Indices da plataforma Deriv, com
profundo conhecimento em análise técnica e no comportamento de volatilidade
sintética. Você opera o índice Volatility 25 (V25). Seu objetivo é analisar
dados de mercado e SEMPRE gerar um sinal direcional de COMPRA ou VENDA com
confiança quantificada, para ser operado dentro do candle de 5 minutos (M5).
Você NUNCA deve retornar AGUARDE — sempre escolha a melhor direção possível
com base nos indicadores disponíveis. Use a confiança (%) para expressar
incerteza (50-55% para sinais fracos, 80%+ para forte confluência).

# DADOS QUE VOCÊ RECEBE

## Candles (via WebSocket da API Deriv)
Cada candle contém:
- epoch  : Unix timestamp do fechamento do candle, em segundos
- open   : preço de abertura do período
- high   : máxima do período
- low    : mínima do período
- close  : preço de fechamento do período

Você recebe dois timeframes:
- M5  (5 minutos)  : timeframe de DECISÃO. O sinal é gerado e operado aqui.
- M15 (15 minutos) : timeframe de CONTEXTO. Define a tendência maior (viés).

## Indicadores técnicos (pré-calculados, parâmetros fixos)
Calculados para M5 e para M15:
- RSI            : período 14
- MACD           : 12 / 26 / 9 (rápida / lenta / sinal)
- Bollinger Bands: período 20, desvio padrão 2
- EMA-50         : média móvel exponencial
- ADX-14         : índice direcional médio (força de tendência)
- ATR-14         : Average True Range (volatilidade)

# CONTEXTO DO MERCADO

Volatility Indices (Volatility 10, 25, 50, 75, 100, 250) são gerados por um
algoritmo de número aleatório auditado e mantêm um nível de volatilidade
constante. NÃO sofrem influência de notícias econômicas, earnings ou eventos
globais — operam 24/7.

- Volatility 10  : movimentos mais lentos e estáveis
- Volatility 25  : movimento moderado, estrutura técnica relativamente limpa
- Volatility 250 : movimentos mais rápidos e amplos

O preço se move de forma algorítmica. Padrões podem ser ruidosos; por isso,
exija confluência e use o M15 como filtro antes de qualquer sinal.

# CONTEXTO DE HORÁRIO

Os horários abaixo são referência geral (UTC e Brasília / BRT, UTC−3). Use-os
para adaptar sua abordagem: em janelas mais favoráveis o movimento tende a ser
mais regular; em janelas desfavoráveis a volatilidade tende a ser mais irregular
e ruidosa. Ajuste o tipo de estratégia que você aplica conforme a janela atual.

Janelas mais favoráveis (movimento mais regular):
- Europa     : 07:00–13:00 UTC  ->  04:00–10:00 BRT
- US Overlap : 14:00–18:00 UTC  ->  11:00–15:00 BRT
- Meio de semana (terça a quinta) tende a ser mais consistente.

Janelas desfavoráveis (volatilidade irregular / mais ruído):
- Late US       : 19:00–23:00 UTC  ->  16:00–20:00 BRT
- Madrugada/Ásia: 00:00–06:00 UTC  ->  21:00–03:00 BRT
- Segunda e domingo tendem a ser mais erráticos.

# DEFINIÇÃO DO REGIME DE MERCADO

Antes de escolher a estratégia, classifique o regime atual usando o ADX-14 do M5:
- ADX > 25  : TENDÊNCIA (use estratégias de tendência / continuação)
- ADX < 20  : RANGE / lateralização (use estratégias de reversão)
- ADX 20–25 : zona indefinida (opere com cautela; escolha o lado com mais confluência)

# ESTRATÉGIAS (operação em M5, contexto em M15)

Escolha a estratégia conforme o regime e a janela de horário.

## A) Tendência (ADX > 25) — janela favorável
Objetivo: operar a favor da tendência maior do M15.
- Confirme o viés no M15: preço acima da EMA-50 = viés de COMPRA; abaixo = viés de VENDA.
- No M5, entre a favor desse viés em pullbacks (correções curtas), não no topo/fundo do impulso.
- Gatilhos de confluência (exija pelo menos 2):
  - MACD do M5 cruzando a linha de sinal na direção do viés
  - Preço repicando na EMA-50 do M5 a favor da tendência
  - RSI saindo de zona neutra na direção do movimento (sem estar já esticado >70 / <30)
- NUNCA opere contra a EMA-50 do M15.

## B) Reversão / Range (ADX < 20) — janela desfavorável ou lateral
Objetivo: operar os extremos do range.
- COMPRA: preço tocando a banda inferior de Bollinger + RSI < 30 + vela de rejeição (ex.: martelo / engolfo de alta).
- VENDA: preço tocando a banda superior de Bollinger + RSI > 70 + vela de rejeição (ex.: estrela cadente / engolfo de baixa).
- Em range, ignore cruzamentos de MACD isolados (geram muito ruído).

## C) Divergências (vale em qualquer regime, alta prioridade)
- Divergência de baixa: preço faz topo mais alto, mas RSI ou MACD faz topo mais baixo -> possível VENDA.
- Divergência de alta: preço faz fundo mais baixo, mas RSI ou MACD faz fundo mais alto -> possível COMPRA.
- Divergência confirmada por vela de reversão é um dos sinais mais fortes.

## D) Suporte e resistência
- Trate S/R como ZONAS (faixas), não linhas finas — o preço costuma "furar" linhas exatas.
- Reações claras em zona conhecida reforçam a confiança do sinal.

# COMO ANALISAR (passo a passo)

1. Defina a tendência maior pelo M15 (posição do preço vs EMA-50 e direção do MACD).
2. Classifique o regime pelo ADX-14 do M5 (tendência, range ou indefinido).
3. Identifique a janela de horário atual (favorável ou desfavorável).
4. Selecione a estratégia adequada (seção ESTRATÉGIAS).
5. Avalie a confluência (2+ sinais concordantes = alta confiança). Sinal isolado ->
   escolha o lado com melhor fundamentação e reduza a confiança (50-55%).
6. Procure divergências e reações em zonas de S/R como confirmação extra.
7. Se houver conflito entre M5 e M15, ou regime indefinido, ou janela ruim sem
   confluência forte -> escolha o lado com mais sinais concordantes e reduza a
   confiança. NUNCA retorne AGUARDE.

# FORMATO DE RESPOSTA

Retorne APENAS três linhas, sem explicações, sem texto adicional:

Linha 1: horário do próximo candle de 5 minutos a ser operado, formato HH:MM
         (calcule a partir do epoch do último candle M5 fechado)
Linha 2: COMPRA  ou  VENDA  (obrigatoriamente um dos dois — NUNCA AGUARDE)
Linha 3: confiança de 0 a 100 (apenas o número, seguido de %)

Exemplo de resposta:
14:40
COMPRA
78%

# TOOLS DISPONÍVEIS

Você tem acesso a tools para investigar dados históricos antes de decidir.
Use-as quando os indicadores atuais forem ambíguos ou quando quiser validar
um padrão com o histórico. Não é obrigatório usá-las em todo ciclo.

- **query_signal_history** — consulta sinais passados (wins/losses) para identificar padrões históricos
- **get_candles_range** — busca candles OHLC históricos para análise de price action (suporta timeframes 5m e 15m)
- **calc_indicator** — recalcula qualquer indicador com parâmetros customizados (ex: RSI-7 em vez de RSI-14)
"""


def build_system_prompt(config: dict) -> str:
    return SYSTEM_PROMPT_TEMPLATE


def build_user_context(
    config: dict,
    m5_indicators: dict,
    m15_indicators: dict,
    pre_analysis: dict,
    last_candle_time: str = "",
    next_entry_time: str = "",
) -> str:
    """Build user context with dual-timeframe indicators and pre-analysis results."""
    # Helper to safely extract values
    def safe_float(val, default=0.0):
        try:
            return float(val) if val is not None else default
        except (TypeError, ValueError):
            return default

    # ===== M5 Indicators Section =====
    m5_close = safe_float(m5_indicators.get("last_close"))
    m5_rsi = safe_float(m5_indicators.get("rsi"))
    m5_rsi_prev3 = m5_indicators.get("rsi_prev3", [])
    m5_close_prev5 = m5_indicators.get("close_prev5", [])
    m5_bb_position = m5_indicators.get("bb_position", "N/A")
    m5_bb_upper = safe_float(m5_indicators.get("bb_upper"))
    m5_bb_lower = safe_float(m5_indicators.get("bb_lower"))
    m5_bb_dist_upper_atr = safe_float(m5_indicators.get("bb_dist_upper_atr"))
    m5_bb_dist_lower_atr = safe_float(m5_indicators.get("bb_dist_lower_atr"))
    m5_ema50 = safe_float(m5_indicators.get("ema50"))
    m5_ema50_dist_atr = safe_float(m5_indicators.get("ema50_dist_atr"))
    m5_adx = safe_float(m5_indicators.get("adx"))
    m5_atr_pct = safe_float(m5_indicators.get("atr_pct"))
    m5_macd_line = m5_indicators.get("macd_line")
    m5_macd_signal = m5_indicators.get("macd_signal")
    m5_macd_histogram = m5_indicators.get("macd_histogram")
    m5_macd_cross = m5_indicators.get("macd_cross", "N/A")

    # M5 RSI trajectory
    m5_rsi_traj = ""
    if len(m5_rsi_prev3) >= 2:
        traj_str = " → ".join(f"{r:.1f}" for r in m5_rsi_prev3)
        if m5_rsi_prev3[-1] > m5_rsi_prev3[0]:
            m5_rsi_dir = "subindo"
        elif m5_rsi_prev3[-1] < m5_rsi_prev3[0]:
            m5_rsi_dir = "caindo"
        else:
            m5_rsi_dir = "estável"
        m5_rsi_traj = f"\n  Trajetória 3 candles: [{traj_str}] ({m5_rsi_dir})"

    # M5 Recent closes
    m5_close_line = ""
    if m5_close_prev5:
        closes_str = ", ".join(f"{c:.2f}" for c in m5_close_prev5)
        if len(m5_close_prev5) >= 2 and m5_close_prev5[0] != 0:
            price_change_pct = (m5_close_prev5[-1] - m5_close_prev5[0]) / m5_close_prev5[0] * 100
            sign = "+" if price_change_pct >= 0 else ""
            m5_close_line = f"Últimos 5 closes: [{closes_str}] (variação: {sign}{price_change_pct:.2f}%)"
        else:
            m5_close_line = f"Últimos 5 closes: [{closes_str}]"

    # M5 MACD line
    m5_macd_line_str = ""
    if m5_macd_line is not None and m5_macd_signal is not None and m5_macd_histogram is not None:
        m5_macd_line_str = (
            f"\nMACD(12,26,9): linha={m5_macd_line:.5f} | sinal={m5_macd_signal:.5f} | "
            f"histograma={m5_macd_histogram:.5f} ({m5_macd_cross})\n"
        )
    else:
        m5_macd_line_str = "\nMACD: dados insuficientes\n"

    # ===== M15 Indicators Section =====
    m15_close = safe_float(m15_indicators.get("last_close"))
    m15_rsi = safe_float(m15_indicators.get("rsi"))
    m15_bb_position = m15_indicators.get("bb_position", "N/A")
    m15_ema50 = safe_float(m15_indicators.get("ema50"))
    m15_price_vs_ema50 = m15_indicators.get("price_vs_ema50", "")
    m15_ema50_dist_atr = safe_float(m15_indicators.get("ema50_dist_atr"))
    m15_adx = safe_float(m15_indicators.get("adx"))
    m15_atr_pct = safe_float(m15_indicators.get("atr_pct"))
    m15_macd_histogram = m15_indicators.get("macd_histogram")
    m15_macd_line = m15_indicators.get("macd_line")
    m15_macd_signal = m15_indicators.get("macd_signal")

    # M15 MACD direction
    if m15_macd_histogram is not None:
        if m15_macd_histogram > 0:
            m15_macd_dir = "positivo"
        elif m15_macd_histogram < 0:
            m15_macd_dir = "negativo"
        else:
            m15_macd_dir = "neutro"
    else:
        m15_macd_dir = "desconhecido"

    # ===== Pre-analysis Section =====
    regime = pre_analysis.get("regime", "UNKNOWN")
    regime_adx = safe_float(pre_analysis.get("regime_adx"))
    time_window = pre_analysis.get("time_window", {})
    m15_bias = pre_analysis.get("m15_bias", {})
    divergences = pre_analysis.get("divergences", {})
    patterns = pre_analysis.get("candlestick_patterns", [])
    sr_zones = pre_analysis.get("sr_zones", [])
    confluence = pre_analysis.get("confluence", {})
    suggested_strategy = pre_analysis.get("suggested_strategy", "NONE")
    suggested_direction = pre_analysis.get("suggested_direction", "CALL")
    suggestion_reasoning = pre_analysis.get("suggestion_reasoning", "")

    # Build pre-analysis block
    pre_analysis_lines = [
        f"\n## Pré-análise de Mercado (Programática)",
        f"Regime: {regime} (ADX M5 = {regime_adx:.1f})",
    ]

    # Time window details
    window_str = time_window.get("window", "UNKNOWN")
    session_str = time_window.get("session", "UNKNOWN")
    day_str = time_window.get("day", "UNKNOWN")
    pre_analysis_lines.append(f"Janela de horário: {window_str} (sessão: {session_str}, dia: {day_str})")

    # M15 bias
    bias_str = m15_bias.get("bias", "UNKNOWN")
    bias_reasoning = m15_bias.get("reasoning", "")
    pre_analysis_lines.append(f"Viés M15 (tendência maior): {bias_str} — {bias_reasoning}")

    # Suggested strategy
    pre_analysis_lines.append(f"Estratégia sugerida: {suggested_strategy} ({suggestion_reasoning})")

    # Divergences
    if divergences.get("details") and "Nenhuma" not in divergences["details"]:
        pre_analysis_lines.append(f"\n### Divergências Detectadas")
        pre_analysis_lines.append(divergences["details"])

    # Candlestick patterns
    if patterns:
        pre_analysis_lines.append(f"\n### Padrões de Candle")
        for p in patterns:
            pre_analysis_lines.append(f"- {p['description']}")

    # S/R zones
    if sr_zones:
        pre_analysis_lines.append(f"\n### Zonas de Suporte/Resistência (top 3 por reações)")
        for zone in sr_zones[:3]:
            zone_type = "Suporte" if zone["type"] == "support" else "Resistência"
            pre_analysis_lines.append(
                f"- {zone_type}: {zone['low']:.2f} - {zone['high']:.2f} ({zone['reactions']} reações)"
            )

    # Confluence score
    call_sig = confluence.get("call_signals", 0)
    put_sig = confluence.get("put_signals", 0)
    pre_analysis_lines.append(f"\n### Confluência de Sinais")
    pre_analysis_lines.append(f"Sinais altista (CALL): {call_sig}")
    pre_analysis_lines.append(f"Sinais baixista (PUT): {put_sig}")
    if confluence.get("details"):
        pre_analysis_lines.append("Detalhes:")
        for detail in confluence["details"][:5]:  # Max 5 details
            pre_analysis_lines.append(f"  - {detail}")

    # ===== Timing Section =====
    timing_section = ""
    if last_candle_time and next_entry_time:
        timing_section = (
            f"\n## Contexto Temporal\n"
            f"- Último candle M5 analisado: {last_candle_time}\n"
            f"- Próximo candle de entrada: {next_entry_time}\n"
            f"- Timeframe de decisão: M5 (5 minutos)\n"
            f"- Timeframe de contexto: M15 (15 minutos)\n"
        )

    # ===== Assemble Full Context =====
    lines = [
        f"Análise de mercado iniciada.",
        f"Ativo: {config.get('symbol', 'R_25')}",
        f"Timeframes: M5 (decisão) + M15 (contexto)",
        "",
        "## Indicadores M5 (Timeframe de Decisão)",
        f"Preço atual: {m5_close:.5f}",
    ]

    if m5_close_line:
        lines.append(m5_close_line)

    lines.extend([
        f"",
        f"RSI-14: {m5_rsi:.1f}{m5_rsi_traj}",
        f"",
        f"Bollinger(20,2): preço {m5_bb_position} da banda",
        f"  Upper: {m5_bb_upper:.5f} ({m5_bb_dist_upper_atr:.2f} ATRs acima do preço)",
        f"  Lower: {m5_bb_lower:.5f} ({m5_bb_dist_lower_atr:.2f} ATRs abaixo do preço)",
        f"",
        f"{m5_macd_line_str.strip()}",
        f"EMA-50: {m5_ema50:.5f} | Preço {'+' if m5_ema50_dist_atr >= 0 else ''}{m5_ema50_dist_atr:.2f} ATRs {'acima' if m5_ema50_dist_atr >= 0 else 'abaixo'}",
        f"ADX-14: {m5_adx:.1f} (<25 fraco, 25-50 moderado, >50 forte)",
        f"ATR-14: {m5_atr_pct:.2f}% (volatilidade por candle)",
        "",
        "## Indicadores M15 (Timeframe de Contexto - Tendência Maior)",
        f"Preço atual: {m15_close:.5f}",
        f"RSI-14: {m15_rsi:.1f}",
        f"Bollinger(20,2): preço {m15_bb_position} da banda",
        f"EMA-50: {m15_ema50:.5f} | Preço {m15_price_vs_ema50} ({m15_ema50_dist_atr:.2f} ATRs)",
        f"MACD histograma: {m15_macd_dir}",
        f"ADX-14: {m15_adx:.1f}",
        f"ATR-14: {m15_atr_pct:.2f}%",
    ])

    # Pre-analysis section
    lines.append("")
    lines.extend(pre_analysis_lines)

    # Timing section
    if timing_section:
        lines.append("")
        lines.append(timing_section.strip())

    # Final instruction
    lines.append("")
    lines.append("Analise os indicadores acima, considere a pré-análise e retorne sua decisão em 3 linhas.")
    lines.append("IMPORTANTE: Você DEVE sempre escolher COMPRA ou VENDA. NUNCA retorne AGUARDE.")
    lines.append("Use a confiança para expressar incerteza (ex: 52% para sinais fracos, 80%+ para forte confluência).")

    return "\n".join(lines)
