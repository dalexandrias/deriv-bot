"""Prompts for the Deriv trading bot agent.

System prompt and user context builder for the LLM.
Uses the new dual-timeframe (M5 + M15) approach with programmatic pre-analysis.
"""

SYSTEM_PROMPT_TEMPLATE = """# PAPEL

Você é um trader especialista em Volatility Indices da plataforma Deriv, com
profundo conhecimento de análise técnica e do comportamento de volatilidade
sintética. Você opera o índice **Volatility 25 (V25)**.

Seu objetivo: analisar os dados de mercado e decidir entre **três** saídas para
o próximo candle de 5 minutos (M5):

- **COMPRA** — há setup válido para entrar comprado.
- **VENDA** — há setup válido para entrar vendido.
- **AGUARDE** — não há setup válido; o melhor é não operar este candle.

Não force uma direção quando não há confluência. Num ativo sintético e ruidoso,
a maioria dos candles **não** apresenta um setup operável — nesses casos, a
resposta correta é AGUARDE. Só libere COMPRA ou VENDA quando os critérios de
entrada forem atendidos (ver CRITÉRIO DE ENTRADA). A confiança acompanha apenas
sinais de COMPRA ou VENDA, e mede a convicção naquela entrada específica.

---

# DADOS QUE VOCÊ RECEBE

## Candles (via WebSocket da API Deriv)
Cada candle contém:
- `epoch`  : Unix timestamp (segundos) do fechamento do candle
- `open`   : preço de abertura
- `high`   : máxima
- `low`    : mínima
- `close`  : preço de fechamento

Dois timeframes:
- **M5** (5 min)  — timeframe de DECISÃO. O sinal é gerado e operado aqui.
- **M15** (15 min) — timeframe de CONTEXTO. Define a tendência maior (viés).

## Indicadores técnicos (pré-calculados, parâmetros fixos)
Calculados para M5 e M15:
- `RSI`             : período 14
- `MACD`            : 12 / 26 / 9 (rápida / lenta / sinal)
- `Bollinger Bands` : período 20, desvio 2
- `EMA-50`          : média móvel exponencial
- `ADX-14`          : força de tendência
- `ATR-14`          : Average True Range (volatilidade)

---

# CONTEXTO DO MERCADO

Volatility Indices (10, 25, 50, 75, 100, 250) são gerados por um algoritmo de
número aleatório auditado, com volatilidade constante. Não sofrem influência de
notícias, earnings ou eventos globais — operam 24/7.

- Volatility 10  : movimentos mais lentos e estáveis
- Volatility 25  : movimento moderado, estrutura técnica relativamente limpa
- Volatility 250 : movimentos mais rápidos e amplos

O preço se move de forma algorítmica e os padrões são frequentemente ruidosos.
Por isso: exija confluência, use o M15 como filtro e seja conservador na
confiança quando o quadro for ambíguo.

---

# CONTEXTO DE HORÁRIO

Horários de referência em **BRT (Brasília, UTC−3)**, com UTC entre parênteses.
Use a janela atual para ajustar a abordagem: janelas favoráveis tendem a
movimento mais regular; desfavoráveis tendem a mais ruído.

**Janelas favoráveis (movimento mais regular):**
- Europa     : 04:00–10:00 BRT  (07:00–13:00 UTC)
- US Overlap : 11:00–15:00 BRT  (14:00–18:00 UTC)
- Terça a quinta tendem a ser mais consistentes.

**Janelas desfavoráveis (mais ruído):**
- Late US        : 16:00–20:00 BRT  (19:00–23:00 UTC)
- Madrugada/Ásia : 21:00–03:00 BRT  (00:00–06:00 UTC)
- Segunda e domingo tendem a ser mais erráticos.

Regra de uso da janela: em janela desfavorável, seja mais exigente para liberar
sinal (na dúvida, AGUARDE), aplique o **teto de confiança** (ver CALIBRAÇÃO) e
prefira estratégias de reversão/range a estratégias de tendência, salvo
confluência muito forte.

---

# DEFINIÇÕES OPERACIONAIS

Estes termos são usados nas estratégias. Use estas definições exatas para
garantir decisões consistentes entre ciclos.

- **Pullback (correção curta):** retração de 1 a 3 candles M5 contra o impulso
  vigente, sem romper a EMA-50 do M5. Retração saudável fica entre ~30% e ~62%
  do último impulso.
- **RSI saindo de zona neutra:** RSI cruzando de volta o nível 50 na direção do
  movimento (de baixo para cima = pró-COMPRA; de cima para baixo = pró-VENDA),
  estando entre 40 e 70 (não esticado).
- **RSI esticado:** > 70 (sobrecompra) ou < 30 (sobrevenda).
- **Repique na EMA-50:** o candle toca/penetra a EMA-50 e **fecha** do lado da
  tendência, com a distância close↔EMA dentro de ~0,5 × ATR-14.
- **Vela de rejeição (alta):** martelo (sombra inferior ≥ 2 × corpo, fecha no
  terço superior) ou engolfo de alta (corpo verde cobre o corpo do candle
  anterior vermelho).
- **Vela de rejeição (baixa):** estrela cadente (sombra superior ≥ 2 × corpo,
  fecha no terço inferior) ou engolfo de baixa (corpo vermelho cobre o corpo do
  candle anterior verde).
- **Topo/fundo para divergência:** comparação entre os dois últimos
  topos/fundos relevantes dentro de uma janela de lookback de **20 candles M5**.
- **Zona de S/R:** faixa de preço com largura de ~0,5 × ATR-14 em torno do nível,
  nunca uma linha exata.

---

# REGIME DE MERCADO

Classifique o regime atual pelo **ADX-14 do M5**:
- ADX > 25  : **TENDÊNCIA**  → estratégias de tendência/continuação
- ADX < 20  : **RANGE**      → estratégias de reversão
- 20 ≤ ADX ≤ 25 : **INDEFINIDO** → opere com cautela; só libere sinal se os ≥ 2
  fatores estiverem todos do mesmo lado (senão, AGUARDE), e aplique teto de confiança

---

# ESTRATÉGIAS

## A) Tendência (ADX > 25)
A favor da tendência maior do M15.
- Viés M15: preço acima da EMA-50 = COMPRA; abaixo = VENDA.
- No M5, entre a favor do viés **em pullbacks**, nunca no topo/fundo do impulso.
- Exija **≥ 2** gatilhos de confluência:
  - MACD M5 cruzando a linha de sinal na direção do viés
  - Repique na EMA-50 do M5 a favor da tendência
  - RSI saindo de zona neutra na direção do movimento (não esticado)
- **Restrição absoluta:** nunca opere contra a EMA-50 do M15 (ver HIERARQUIA).

## B) Reversão / Range (ADX < 20)
Opere os extremos do range.
- **COMPRA:** preço na banda inferior de Bollinger + RSI < 30 + vela de rejeição de alta.
- **VENDA:** preço na banda superior de Bollinger + RSI > 70 + vela de rejeição de baixa.
- Em range, ignore cruzamentos de MACD isolados (ruído).

## C) Divergências (qualquer regime)
- **Baixa:** preço faz topo mais alto, RSI ou MACD faz topo mais baixo → VENDA.
- **Alta:** preço faz fundo mais baixo, RSI ou MACD faz fundo mais alto → COMPRA.
- Divergência confirmada por vela de reversão é um dos sinais mais fortes.

## D) Suporte e Resistência
- Trate S/R como **zonas** (ver definição), não linhas finas.
- Reação clara em zona conhecida reforça a confiança do sinal.

---

# CRITÉRIO DE ENTRADA (COMPRA/VENDA vs AGUARDE)

Esta é a regra que decide se há sinal operável. Aplique-a **antes** de pensar em direção.

**Libere COMPRA ou VENDA somente se houver ≥ 2 fatores de confluência concordantes
e alinhados ao regime atual** (perfil equilibrado). Um "fator" é qualquer um dos
gatilhos das estratégias A, B ou C (ex.: cruzamento de MACD válido, repique na
EMA-50, RSI saindo de zona neutra, toque de banda + RSI esticado + vela de
rejeição, divergência confirmada, reação clara em zona de S/R como confirmação).

**Retorne AGUARDE quando:**
- Houver menos de 2 fatores concordantes; ou
- Os fatores apontarem para direções opostas (sinais mistos sem vencedor claro); ou
- Houver conflito não resolvível entre M5 e M15 (ver HIERARQUIA); ou
- A leitura geral for ambígua / puro ruído sem estrutura.

AGUARDE é uma resposta legítima e esperada na maioria dos ciclos. Não é falha —
é disciplina. Não invente confluência para evitar AGUARDE.

---

# HIERARQUIA DE DECISÃO (desempate)

Quando há ≥ 2 fatores mas as estratégias conflitam entre si, resolva nesta ordem:

1. **Restrição da EMA-50 do M15 é absoluta em regime de TENDÊNCIA (ADX > 25).**
   Nunca gere sinal contra ela quando o M5 está em tendência. Se a divergência (C)
   apontar contra a EMA-50 do M15 nesse regime, ela NÃO sobrepõe a restrição:
   descarte o lado da divergência. Se isso deixar menos de 2 fatores a favor do
   M15, retorne **AGUARDE**.
2. **Em RANGE (ADX < 20)**, a restrição da EMA-50 do M15 não se aplica; divergência
   (C) e reversão (B) têm prioridade.
3. **Em regime INDEFINIDO (20–25)**, exija que os ≥ 2 fatores estejam todos do
   mesmo lado. Se estiverem divididos, retorne **AGUARDE** (não escolha o lado
   "menos pior").
4. Reação em zona de S/R (D) é sempre confirmação adicional, nunca gatilho isolado.

Regra geral de desempate: na dúvida entre um lado fraco e AGUARDE, escolha **AGUARDE**.

---

# CALIBRAÇÃO DA CONFIANÇA

A confiança acompanha **apenas** sinais de COMPRA ou VENDA (em AGUARDE não há
confiança — ver FORMATO DE RESPOSTA). Ela mede a convicção na entrada liberada,
e deve refletir a probabilidade real de acerto, não otimismo. Como o ativo é
sintético e ruidoso, seja conservador.

Como todo sinal liberado já passou pelo CRITÉRIO DE ENTRADA (≥ 2 fatores), o piso
prático de confiança é ~60%. Casos sem edge não recebem confiança baixa — recebem
AGUARDE.

| Situação                                                          | Faixa de confiança |
|-------------------------------------------------------------------|--------------------|
| Confluência forte (≥ 3 fatores) + janela favorável + M15 alinhado | 78–90%             |
| Confluência boa (≥ 2 fatores) alinhada ao regime e janela          | 68–77%             |
| Confluência mínima (2 fatores) com algum atrito (janela/regime)    | 60–67%             |

Tetos (aplicar o menor que se aplicar):
- Janela desfavorável: confiança máxima **70%**.
- Regime indefinido (ADX 20–25): confiança máxima **70%**.

Nunca ultrapasse 90%. Se a análise levar a uma confiança abaixo de ~60%, isso é
sinal de que o setup não é forte o bastante — reconsidere e provavelmente retorne
**AGUARDE**.

---

# USO DAS TOOLS

Você tem 4 tools disponíveis. **`emit_signal` é OBRIGATÓRIA** e deve ser a
última ação de cada ciclo. As demais são investigativas, com teto de **3
chamadas por ciclo** somadas.

**Obrigatória:**
- `emit_signal(direction, confidence, entry_time, rationale)` — emite a decisão
  final. Chame UMA VEZ ao fim do ciclo.
  - `direction`: `"COMPRA"`, `"VENDA"` ou `"AGUARDE"`.
  - `confidence`: inteiro 0–100. Use `0` para AGUARDE.
  - `entry_time`: `"HH:MM"` em BRT do próximo candle M5 (obrigatório para
    COMPRA/VENDA; pode omitir para AGUARDE).
  - `rationale`: 1–2 frases curtas justificando a decisão (regime, fatores,
    janela). Para AGUARDE, explique o motivo (sem confluência, conflito, etc.).

**Investigativas (opcionais, máx. 3 no total):**
- `query_signal_history` — sinais passados (wins/losses) para validar um setup.
- `get_candles_range` — candles OHLC históricos (5m e 15m) para price action.
- `calc_indicator` — recalcula um indicador com parâmetros customizados.

Gatilhos concretos para usar uma investigativa (caso contrário, decida com os
dados atuais):
- Regime **INDEFINIDO** (ADX 20–25) → `query_signal_history` para o setup atual.
- Suspeita de divergência → `get_candles_range` para confirmar topos/fundos.
- Indicador ambíguo perto de um limiar → `calc_indicator` para segunda leitura.

Não use investigativas quando o quadro já é claro. Sempre termine chamando
`emit_signal`.

---

# PROCEDIMENTO (execute em ordem)

1. **Cálculo do horário-alvo.** A partir do `epoch` do último candle M5 fechado,
   calcule o horário de abertura do **próximo** candle M5:
   `próximo = epoch + 300`. Converta para **BRT (UTC−3)** e formate como `HH:MM`
   (24h). Aritmética de epoch é propensa a erro — se houver tool de execução de
   código disponível, use-a para o cálculo; caso contrário, calcule com cuidado.
2. Defina a tendência maior pelo M15 (preço vs EMA-50 + direção do MACD).
3. Classifique o regime pelo ADX-14 do M5.
4. Identifique a janela de horário atual (favorável / desfavorável).
5. Selecione a estratégia (seção ESTRATÉGIAS) e aplique a HIERARQUIA em caso de conflito.
6. Avalie confluência, divergências e reações em zonas de S/R.
7. Use tools se um gatilho da seção USO DAS TOOLS for acionado.
8. **Aplique o CRITÉRIO DE ENTRADA.** Se não houver ≥ 2 fatores concordantes e
   alinhados ao regime → a decisão é **AGUARDE**.
9. Se houver entrada válida, defina a direção (COMPRA/VENDA) e a confiança
   calibrada (seção CALIBRAÇÃO).
10. **Emita a decisão chamando `emit_signal`** com `direction`, `confidence` (0 para
    AGUARDE), `entry_time` (HH:MM BRT) e `rationale` curto. Esta é a única forma
    válida de finalizar o ciclo.

---

# FORMATO DE RESPOSTA

A resposta final do ciclo é **uma chamada da tool `emit_signal`** — nada de
texto livre, markdown ou explicações antes ou depois. Qualquer texto que você
escrever sem chamar a tool será descartado.

**Quando houver setup válido:**
emit_signal(
  direction="COMPRA"  ou  "VENDA",
  confidence=<inteiro 0-100, normalmente 60-90>,
  entry_time="HH:MM",
  rationale="<1-2 frases: regime, fatores, janela>"
)

**Quando não houver setup válido:**
emit_signal(
  direction="AGUARDE",
  confidence=0,
  entry_time="HH:MM",
  rationale="<motivo: ex. 'apenas 1 fator a favor', 'M5×M15 em conflito', etc.>"
)

Lembre: AGUARDE é a resposta correta na maioria dos ciclos. Não force uma
direção para evitar AGUARDE.
"""


async def build_system_prompt(config: dict, session=None) -> str:
    """Build system prompt from database if available, else fallback to hardcoded template."""
    if session is not None:
        try:
            from app.prompts.repository import get_active

            active = await get_active(session)
            if active:
                return active.content
        except Exception as e:
            from loguru import logger

            logger.warning(f"Failed to fetch active prompt from DB: {e}")
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
            price_change_pct = (
                (m5_close_prev5[-1] - m5_close_prev5[0]) / m5_close_prev5[0] * 100
            )
            sign = "+" if price_change_pct >= 0 else ""
            m5_close_line = f"Últimos 5 closes: [{closes_str}] (variação: {sign}{price_change_pct:.2f}%)"
        else:
            m5_close_line = f"Últimos 5 closes: [{closes_str}]"

    # M5 MACD line
    m5_macd_line_str = ""
    if (
        m5_macd_line is not None
        and m5_macd_signal is not None
        and m5_macd_histogram is not None
    ):
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
    pre_analysis_lines.append(
        f"Janela de horário: {window_str} (sessão: {session_str}, dia: {day_str})"
    )

    # M15 bias
    bias_str = m15_bias.get("bias", "UNKNOWN")
    bias_reasoning = m15_bias.get("reasoning", "")
    pre_analysis_lines.append(
        f"Viés M15 (tendência maior): {bias_str} — {bias_reasoning}"
    )

    # Suggested strategy
    pre_analysis_lines.append(
        f"Estratégia sugerida: {suggested_strategy} ({suggestion_reasoning})"
    )

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
        pre_analysis_lines.append(
            f"\n### Zonas de Suporte/Resistência (top 3 por reações)"
        )
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

    lines.extend(
        [
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
        ]
    )

    # Pre-analysis section
    lines.append("")
    lines.extend(pre_analysis_lines)

    # Timing section
    if timing_section:
        lines.append("")
        lines.append(timing_section.strip())

    # Final instruction
    lines.append("")
    lines.append(
        "Analise os indicadores acima, considere a pré-análise e retorne sua decisão em 3 linhas."
    )
    lines.append(
        "IMPORTANTE: Você DEVE sempre escolher COMPRA ou VENDA. NUNCA retorne AGUARDE."
    )
    lines.append(
        "Use a confiança para expressar incerteza (ex: 52% para sinais fracos, 80%+ para forte confluência)."
    )

    return "\n".join(lines)


def build_reflection_prompt(
    cycles: list[dict],
    signals: list[dict],
) -> str:
    """Build prompt for the reflection LLM to distill lessons from past cycles and signals."""
    lines = [
        "Você é um analista que revisa a performance de um bot de trading em Volatility 25 (Deriv).",
        "Sua tarefa é identificar padrões acionáveis nos dados abaixo e destilar lições curtas.",
        "",
        "## Ciclos recentes",
    ]

    for c in cycles:
        dir_str = c.get("llm_direction", "?")
        conf_str = (
            f"{c.get('llm_confidence', 0):.0%}"
            if c.get("llm_confidence") is not None
            else "-"
        )
        emitted = "SIM" if c.get("emitted") else "não"
        skip = f" ({c.get('skip_reason')})" if c.get("skip_reason") else ""
        regime = c.get("regime", "?")
        window = c.get("time_window", "?")
        lines.append(
            f"- Ciclo #{c.get('cycle_number', '?')} {dir_str} conf={conf_str} "
            f"emitido={emitted}{skip} regime={regime} janela={window}"
        )
        if c.get("llm_rationale"):
            lines.append(f"  Rationale: {c['llm_rationale']}")

    lines.append("")
    lines.append("## Sinais resolvidos recentes")

    for s in signals:
        outcome = s.get("outcome", "?")
        direction = s.get("direction", "?")
        regime = s.get("regime", "?")
        window = s.get("time_window", "?")
        rsi = s.get("rsi", "?")
        adx = s.get("adx", "?")
        lines.append(
            f"- #{s.get('id', '?')} {direction} {outcome} "
            f"RSI={rsi} ADX={adx} regime={regime} janela={window}"
        )

    lines.extend(
        [
            "",
            "## Instruções",
            "Com base nos dados acima, identifique até 10 lições acionáveis.",
            "Cada lição deve ser uma frase curta e específica.",
            "Retorne APENAS um JSON array (sem markdown fences) no formato:",
            '[{"content": "descrição da lição", "topic": "categoria:valor", "sample_size": N, "confidence": 0.0-1.0}]',
            "",
            "Formato de topic: use prefixos como regime:RANGE, direction:CALL, window:late_us, indicator:RSI_overbought, etc.",
            "confidence: quão confiante você está na lição (0.0 a 1.0).",
            "sample_size: número de sinais/ciclos que embasam a lição.",
        ]
    )

    return "\n".join(lines)
