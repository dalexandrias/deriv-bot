"""Programmatic market pre-analysis module.

Computes deterministic analysis steps:
- Market regime classification (TREND/RANGE/UNDEFINED based on ADX)
- Time window classification (FAVORABLE/UNFAVORABLE based on UTC hour and day)
- M15 trend bias determination (BULLISH/BEARISH/NEUTRAL)
- Divergence detection (delegated to indicators.technical)
- Candlestick pattern detection (delegated to indicators.technical)
- S/R zone detection (delegated to indicators.technical)
- Confluence scoring
- Strategy suggestion

All results are passed as structured context to the LLM for final decision.
"""

from datetime import datetime, timezone, timedelta
from app.indicators.technical import detect_divergences, detect_candlestick_patterns, detect_sr_zones


def classify_market_regime(m5_indicators: dict) -> str:
    """Classify market regime based on M5 ADX-14.

    Returns:
        "TREND" | "RANGE" | "UNDEFINED"
    """
    adx = m5_indicators.get("adx", 0)
    if adx > 25:
        return "TREND"
    elif adx < 20:
        return "RANGE"
    else:
        return "UNDEFINED"


def classify_time_window() -> dict:
    """Classify current time as favorable/unfavorable for trading.

    Returns:
        dict with:
        - window: "FAVORABLE" | "UNFAVORABLE"
        - session: "EUROPE" | "US_OVERLAP" | "LATE_US" | "ASIA" | "OTHER"
        - day: weekday name in Portuguese
        - day_quality: "good" | "poor" | "neutral"
    """
    utc_now = datetime.now(timezone.utc)
    hour = utc_now.hour
    weekday = utc_now.weekday()  # 0 = Monday, 6 = Sunday

    # Map weekday to Portuguese
    day_names_pt = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    day_name = day_names_pt[weekday]

    # Determine session
    if 7 <= hour < 13:
        session = "EUROPE"
        session_quality = "good"
    elif 14 <= hour < 18:
        session = "US_OVERLAP"
        session_quality = "good"
    elif 19 <= hour < 23:
        session = "LATE_US"
        session_quality = "poor"
    elif 0 <= hour < 6:
        session = "ASIA"
        session_quality = "poor"
    else:
        session = "OTHER"
        session_quality = "neutral"

    # Day quality (Tue-Thu are best, Mon/Sun are worst)
    if 1 <= weekday <= 3:  # Tue, Wed, Thu
        day_quality = "good"
    elif weekday == 0 or weekday == 6:  # Mon, Sun
        day_quality = "poor"
    else:  # Fri, Sat
        day_quality = "neutral"

    # Combined: favorable if session is good AND day is good/neutral
    if session_quality == "good" and day_quality in ("good", "neutral"):
        window = "FAVORABLE"
    else:
        window = "UNFAVORABLE"

    return {
        "window": window,
        "session": session,
        "day": day_name,
        "day_quality": day_quality,
        "hour_utc": hour
    }


def determine_m15_bias(m15_indicators: dict) -> dict:
    """Determine M15 trend bias.

    Returns:
        dict with:
        - bias: "BULLISH" | "BEARISH" | "NEUTRAL"
        - price_vs_ema50: "acima" | "abaixo"
        - macd_direction: "up" | "down" | "neutral"
        - reasoning: str
    """
    price_vs_ema50 = m15_indicators.get("price_vs_ema50", "")
    macd_histogram = m15_indicators.get("macd_histogram", 0)

    if macd_histogram is None:
        macd_direction = "neutral"
    elif macd_histogram > 0:
        macd_direction = "up"
    elif macd_histogram < 0:
        macd_direction = "down"
    else:
        macd_direction = "neutral"

    # Determine bias
    if price_vs_ema50 == "acima" and macd_direction == "up":
        bias = "BULLISH"
        reasoning = "Preço acima da EMA-50 e histograma MACD positivo"
    elif price_vs_ema50 == "abaixo" and macd_direction == "down":
        bias = "BEARISH"
        reasoning = "Preço abaixo da EMA-50 e histograma MACD negativo"
    else:
        bias = "NEUTRAL"
        reasoning = f"Preço {price_vs_ema50} da EMA-50 com MACD {macd_direction} (sinais mistos)"

    return {
        "bias": bias,
        "price_vs_ema50": price_vs_ema50,
        "macd_direction": macd_direction,
        "macd_histogram": macd_histogram,
        "reasoning": reasoning
    }


def calculate_confluence(
    m5_indicators: dict,
    m15_indicators: dict,
    regime: str,
    m15_bias: dict,
    divergences: dict,
    patterns: list,
    sr_zones: list
) -> dict:
    """Count confirming signals for each direction.

    Returns:
        dict with:
        - call_signals: int (count of bullish confirmations)
        - put_signals: int (count of bearish confirmations)
        - details: list of strings describing each signal
    """
    call_signals = 0
    put_signals = 0
    details = []

    # 1. RSI extremes
    rsi = m5_indicators.get("rsi", 50)
    if rsi < 30:
        call_signals += 1
        details.append(f"RSI sobrevendido ({rsi:.1f} < 30) → CALL")
    elif rsi > 70:
        put_signals += 1
        details.append(f"RSI sobrecomprado ({rsi:.1f} > 70) → PUT")

    # 2. Bollinger Bands extremes
    bb_position = m5_indicators.get("bb_position", "")
    if bb_position == "abaixo":
        call_signals += 1
        details.append(f"Preço abaixo da banda inferior de BB → CALL")
    elif bb_position == "acima":
        put_signals += 1
        details.append(f"Preço acima da banda superior de BB → PUT")

    # 3. MACD crossover
    macd_cross = m5_indicators.get("macd_cross", "")
    if macd_cross == "cruzamento_alta":
        call_signals += 1
        details.append("MACD cruzamento de alta → CALL")
    elif macd_cross == "cruzamento_baixa":
        put_signals += 1
        details.append("MACD cruzamento de baixa → PUT")

    # 4. M15 bias alignment
    if m15_bias["bias"] == "BULLISH":
        call_signals += 1
        details.append(f"Viés M15 altista ({m15_bias['reasoning']}) → CALL")
    elif m15_bias["bias"] == "BEARISH":
        put_signals += 1
        details.append(f"Viés M15 baixista ({m15_bias['reasoning']}) → PUT")

    # 5. Divergences
    if divergences.get("bullish_rsi_divergence") or divergences.get("bullish_macd_divergence"):
        call_signals += 1
        details.append(f"Divergência altista detectada → CALL")
    if divergences.get("bearish_rsi_divergence") or divergences.get("bearish_macd_divergence"):
        put_signals += 1
        details.append(f"Divergência baixista detectada → PUT")

    # 6. Candlestick patterns
    for p in patterns:
        if p["direction"] == "bullish":
            call_signals += 1
            details.append(f"Padrão {p['pattern']} detectado → CALL")
        elif p["direction"] == "bearish":
            put_signals += 1
            details.append(f"Padrão {p['pattern']} detectado → PUT")

    # 7. S/R zone reactions (if current price is near a zone)
    last_close = m5_indicators.get("last_close", 0)
    if last_close > 0:
        for zone in sr_zones[:3]:  # Check top 3 zones
            zone_low = zone["low"]
            zone_high = zone["high"]
            if zone_low <= last_close <= zone_high:
                if zone["type"] == "support":
                    call_signals += 1
                    details.append(f"Preço em zona de suporte ({zone_low:.2f}-{zone_high:.2f}) → CALL")
                elif zone["type"] == "resistance":
                    put_signals += 1
                    details.append(f"Preço em zona de resistência ({zone_low:.2f}-{zone_high:.2f}) → PUT")

    return {
        "call_signals": call_signals,
        "put_signals": put_signals,
        "details": details
    }


def _resolve_direction(confluence: dict, m5_indicators: dict, m15_indicators: dict) -> str:
    """Resolve para CALL ou PUT usando confluência e indicadores como desempate.

    Prioridade:
    1. Lado com mais sinais de confluência
    2. Direção do histograma MACD M5
    3. Posição do preço vs EMA-50 M15
    4. Fallback: CALL
    """
    call_signals = confluence.get("call_signals", 0)
    put_signals = confluence.get("put_signals", 0)

    if call_signals > put_signals:
        return "CALL"
    if put_signals > call_signals:
        return "PUT"

    # Empate — desempatar pelo MACD M5
    macd_hist = m5_indicators.get("macd_histogram")
    if macd_hist is not None:
        if macd_hist > 0:
            return "CALL"
        if macd_hist < 0:
            return "PUT"

    # MACD neutro — usar posição vs EMA-50 M15
    price_vs_ema50 = m15_indicators.get("price_vs_ema50", "")
    if price_vs_ema50 == "acima":
        return "CALL"
    if price_vs_ema50 == "abaixo":
        return "PUT"

    return "CALL"


def run_pre_analysis(
    m5_indicators: dict,
    m15_indicators: dict,
    m5_candles: list,
    m15_candles: list
) -> dict:
    """Main entry point. Runs all pre-analysis steps.

    Args:
        m5_indicators: Dict from analyze() on M5 candles
        m15_indicators: Dict from analyze() on M15 candles
        m5_candles: List of M5 candle dicts
        m15_candles: List of M15 candle dicts

    Returns:
        dict with all pre-analysis results:
        - regime: "TREND" | "RANGE" | "UNDEFINED"
        - regime_adx: float (the ADX value used for classification)
        - time_window: dict from classify_time_window()
        - m15_bias: dict from determine_m15_bias()
        - divergences: dict from detect_divergences()
        - candlestick_patterns: list from detect_candlestick_patterns()
        - sr_zones: list from detect_sr_zones()
        - confluence: dict from calculate_confluence()
        - suggested_strategy: "TREND" | "REVERSAL" | "DIVERGENCE" | "SR" | "NONE"
        - suggested_direction: "CALL" | "PUT"
    """
    # 1. Classify market regime
    regime = classify_market_regime(m5_indicators)
    regime_adx = m5_indicators.get("adx", 0)

    # 2. Classify time window
    time_window = classify_time_window()

    # 3. Determine M15 bias
    m15_bias = determine_m15_bias(m15_indicators)

    # 4. Detect divergences
    rsi_series = m5_indicators.get("rsi_series_last10", [])
    macd_hist_series = m5_indicators.get("macd_hist_series_last10", [])
    divergences = detect_divergences(m5_candles, rsi_series, macd_hist_series)

    # 5. Detect candlestick patterns
    candlestick_patterns = detect_candlestick_patterns(m5_candles)

    # 6. Detect S/R zones
    atr = m5_indicators.get("atr", 0)
    sr_zones = detect_sr_zones(m5_candles, atr)

    # 7. Calculate confluence
    confluence = calculate_confluence(
        m5_indicators, m15_indicators, regime, m15_bias,
        divergences, candlestick_patterns, sr_zones
    )

    # 8. Suggest strategy based on regime + time window + other factors
    suggested_strategy = "NONE"
    suggested_direction = "CALL"
    suggestion_reasoning = ""

    # Divergence is highest priority (any regime)
    has_bullish_div = (divergences.get("bullish_rsi_divergence") or
                       divergences.get("bullish_macd_divergence"))
    has_bearish_div = (divergences.get("bearish_rsi_divergence") or
                       divergences.get("bearish_macd_divergence"))

    if has_bullish_div or has_bearish_div:
        suggested_strategy = "DIVERGENCE"
        if has_bullish_div and not has_bearish_div:
            suggested_direction = "CALL"
        elif has_bearish_div and not has_bullish_div:
            suggested_direction = "PUT"
        else:
            suggested_direction = _resolve_direction(confluence, m5_indicators, m15_indicators)
        suggestion_reasoning = "Divergência detectada (alta prioridade)"

    elif regime == "TREND" and time_window["window"] == "FAVORABLE":
        suggested_strategy = "TREND"
        if m15_bias["bias"] == "BULLISH":
            suggested_direction = "CALL"
        elif m15_bias["bias"] == "BEARISH":
            suggested_direction = "PUT"
        else:
            suggested_direction = _resolve_direction(confluence, m5_indicators, m15_indicators)
        suggestion_reasoning = f"Regime de tendência (ADX={regime_adx:.1f}) em janela favorável"

    elif regime == "RANGE":
        suggested_strategy = "REVERSAL"
        if confluence["call_signals"] >= 2:
            suggested_direction = "CALL"
        elif confluence["put_signals"] >= 2:
            suggested_direction = "PUT"
        else:
            suggested_direction = _resolve_direction(confluence, m5_indicators, m15_indicators)
        suggestion_reasoning = f"Regime de range (ADX={regime_adx:.1f}) - buscar reversão nos extremos"

    elif sr_zones and len(sr_zones) > 0:
        # Check if price is at a significant S/R zone
        last_close = m5_indicators.get("last_close", 0)
        at_significant_zone = False
        for zone in sr_zones[:2]:  # Top 2 zones
            if zone["low"] <= last_close <= zone["high"] and zone["reactions"] >= 3:
                at_significant_zone = True
                suggested_strategy = "SR"
                if zone["type"] == "support":
                    suggested_direction = "CALL"
                else:
                    suggested_direction = "PUT"
                suggestion_reasoning = f"Preço em zona de {zone['type']} com {zone['reactions']} reações"
                break

        if not at_significant_zone and suggested_strategy == "NONE":
            suggested_strategy = "CONFLUENCE"
            suggested_direction = _resolve_direction(confluence, m5_indicators, m15_indicators)
            suggestion_reasoning = "Sem zona S/R significativa — direção por confluência"

    elif regime == "UNDEFINED":
        suggested_strategy = "CONFLUENCE"
        suggested_direction = _resolve_direction(confluence, m5_indicators, m15_indicators)
        suggestion_reasoning = f"Regime indefinido (ADX={regime_adx:.1f} na zona 20-25) — direção por confluência"

    else:
        # Default: always resolve to a direction
        suggested_strategy = "CONFLUENCE"
        suggested_direction = _resolve_direction(confluence, m5_indicators, m15_indicators)
        suggestion_reasoning = "Direção resolvida por confluência e desempate técnico"

    return {
        "regime": regime,
        "regime_adx": regime_adx,
        "time_window": time_window,
        "m15_bias": m15_bias,
        "divergences": divergences,
        "candlestick_patterns": candlestick_patterns,
        "sr_zones": sr_zones,
        "confluence": confluence,
        "suggested_strategy": suggested_strategy,
        "suggested_direction": suggested_direction,
        "suggestion_reasoning": suggestion_reasoning
    }
