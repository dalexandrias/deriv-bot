import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, ADXIndicator, MACD
from ta.volatility import BollingerBands, AverageTrueRange


def analyze(candles: list[dict]) -> dict:
    if not candles:
        raise ValueError("Lista de candles vazia")

    df = pd.DataFrame(candles)
    for col in ("open", "high", "low", "close"):
        df.loc[:, col] = df[col].astype(float)

    close = df["close"]

    # RSI-14 (único oscilador de momentum)
    rsi_series = RSIIndicator(close=close, window=14).rsi()
    rsi = float(rsi_series.iloc[-1]) if not rsi_series.empty else float("nan")
    if pd.isna(rsi):
        rsi_signal = "neutro"
    elif rsi > 70:
        rsi_signal = "sobrecomprado"
    elif rsi < 30:
        rsi_signal = "sobrevendido"
    else:
        rsi_signal = "neutro"

    # Bollinger Bands (envelope de volatilidade)
    bb = BollingerBands(close=close, window=20, window_dev=2)
    bb_upper = float(bb.bollinger_hband().iloc[-1])
    bb_lower = float(bb.bollinger_lband().iloc[-1])
    last_close = float(close.iloc[-1])
    if last_close > bb_upper:
        bb_position = "acima"
    elif last_close < bb_lower:
        bb_position = "abaixo"
    else:
        bb_position = "dentro"

    # EMA-50 (filtro de tendência)
    ema50_series = EMAIndicator(close=close, window=50).ema_indicator()
    ema50 = float(ema50_series.iloc[-1]) if not ema50_series.empty else last_close
    price_vs_ema50 = "acima" if last_close > ema50 else "abaixo"

    # ADX-14 (força da tendência, valor bruto) — needs ≥ 28 candles
    try:
        adx_indicator = ADXIndicator(high=df["high"], low=df["low"], close=close, window=14)
        adx_series = adx_indicator.adx()
        adx_raw = adx_series.dropna()
        adx = float(adx_raw.iloc[-1]) if not adx_raw.empty else float("nan")
    except Exception:
        adx = float("nan")

    # ATR-14 (volatilidade)
    atr_indicator = AverageTrueRange(high=df["high"], low=df["low"], close=close, window=14)
    atr_series = atr_indicator.average_true_range()
    atr = float(atr_series.iloc[-1]) if not atr_series.empty else 0.0
    atr_pct = (atr / last_close * 100) if last_close != 0 else 0.0

    # MACD(12, 26, 9) — indicador de tendência com cruzamentos
    macd_obj = MACD(close=close, window_fast=12, window_slow=26, window_sign=9)
    macd_line_series = macd_obj.macd()
    macd_signal_series = macd_obj.macd_signal()
    macd_hist_series = macd_obj.macd_diff()

    macd_line = float(macd_line_series.iloc[-1]) if not macd_line_series.empty and pd.notna(macd_line_series.iloc[-1]) else float("nan")
    macd_signal = float(macd_signal_series.iloc[-1]) if not macd_signal_series.empty and pd.notna(macd_signal_series.iloc[-1]) else float("nan")
    macd_histogram = float(macd_hist_series.iloc[-1]) if not macd_hist_series.empty and pd.notna(macd_hist_series.iloc[-1]) else float("nan")

    # Detectar cruzamento: comparar últimos 2 valores do histograma
    macd_hist_clean = macd_hist_series.dropna()
    if len(macd_hist_clean) >= 2:
        prev_hist = float(macd_hist_clean.iloc[-2])
        curr_hist = float(macd_hist_clean.iloc[-1])
        if prev_hist <= 0 and curr_hist > 0:
            macd_cross = "cruzamento_alta"
        elif prev_hist >= 0 and curr_hist < 0:
            macd_cross = "cruzamento_baixa"
        else:
            macd_cross = "sem_cruzamento"
    else:
        macd_cross = "dados_insuficientes"

    # RSI trajectory: last 3 values for momentum detection
    rsi_clean = rsi_series.dropna()
    rsi_prev3 = [round(float(v), 2) for v in rsi_clean.iloc[-3:].tolist()] if len(rsi_clean) >= 3 else []

    # Recent closes: last 5 candles
    close_prev5 = [round(float(v), 5) for v in close.iloc[-5:].tolist()]

    # Distances to BB bands and EMA-50 expressed in ATR units
    if atr > 0:
        bb_dist_upper_atr = round((bb_upper - last_close) / atr, 2)
        bb_dist_lower_atr = round((last_close - bb_lower) / atr, 2)
        ema50_dist_atr = round((last_close - ema50) / atr, 2)
    else:
        bb_dist_upper_atr = 0.0
        bb_dist_lower_atr = 0.0
        ema50_dist_atr = 0.0

    return {
        "last_close": round(last_close, 5),
        "candles_count": len(candles),
        "rsi": round(rsi, 2),
        "rsi_signal": rsi_signal,
        "rsi_prev3": rsi_prev3,
        "close_prev5": close_prev5,
        "bb_upper": round(bb_upper, 5),
        "bb_lower": round(bb_lower, 5),
        "bb_position": bb_position,
        "bb_dist_upper_atr": bb_dist_upper_atr,
        "bb_dist_lower_atr": bb_dist_lower_atr,
        "ema50": round(ema50, 5),
        "price_vs_ema50": price_vs_ema50,
        "ema50_dist_atr": ema50_dist_atr,
        "adx": round(adx, 2),
        "atr": round(atr, 5),
        "atr_pct": round(atr_pct, 2),
        "macd_line": round(macd_line, 5) if pd.notna(macd_line) else None,
        "macd_signal": round(macd_signal, 5) if pd.notna(macd_signal) else None,
        "macd_histogram": round(macd_histogram, 5) if pd.notna(macd_histogram) else None,
        "macd_cross": macd_cross,
        # Series for divergence detection (last 10 values)
        "rsi_series_last10": [round(float(v), 2) for v in rsi_series.dropna().iloc[-10:].tolist()] if len(rsi_series.dropna()) >= 10 else [],
        "macd_hist_series_last10": [round(float(v), 5) for v in macd_hist_series.dropna().iloc[-10:].tolist()] if len(macd_hist_series.dropna()) >= 10 else [],
    }


def detect_divergences(candles: list[dict], rsi_series: list[float], macd_hist_series: list[float]) -> dict:
    """Detect divergences between price and indicators.
    Returns dict with bearish/bullish divergence flags for RSI and MACD."""
    if len(candles) < 5 or len(rsi_series) < 5 or len(macd_hist_series) < 5:
        return {
            "bearish_rsi_divergence": False,
            "bullish_rsi_divergence": False,
            "bearish_macd_divergence": False,
            "bullish_macd_divergence": False,
            "details": "Dados insuficientes para deteção de divergência"
        }

    # Get last 5 candles for price analysis
    df = pd.DataFrame(candles[-5:])
    for col in ("open", "high", "low", "close"):
        df.loc[:, col] = df[col].astype(float)

    # Find recent highs and lows (using close prices)
    closes = df["close"].tolist()

    # Simple peak detection: find local maxima and minima
    recent_highs = []
    recent_lows = []

    for i in range(1, len(closes) - 1):
        if closes[i] > closes[i-1] and closes[i] > closes[i+1]:
            recent_highs.append((i, closes[i]))
        if closes[i] < closes[i-1] and closes[i] < closes[i+1]:
            recent_lows.append((i, closes[i]))

    # Map RSI and MACD values to same indices
    rsi_last5 = rsi_series[-5:] if len(rsi_series) >= 5 else rsi_series
    macd_last5 = macd_hist_series[-5:] if len(macd_hist_series) >= 5 else macd_hist_series

    bearish_rsi = False
    bullish_rsi = False
    bearish_macd = False
    bullish_macd = False
    details = []

    # Check bearish divergence (price higher high, indicator lower high)
    if len(recent_highs) >= 2:
        price_highs = [h[1] for h in recent_highs[-2:]]
        if price_highs[-1] > price_highs[0]:
            # Price made higher high
            rsi_at_highs = [rsi_last5[min(h[0], len(rsi_last5)-1)] for h in recent_highs[-2:]]
            macd_at_highs = [macd_last5[min(h[0], len(macd_last5)-1)] for h in recent_highs[-2:]]

            if len(rsi_at_highs) >= 2 and rsi_at_highs[-1] < rsi_at_highs[0]:
                bearish_rsi = True
                details.append(f"Divergência baixista RSI: preço topo mais alto ({price_highs[-1]:.2f} > {price_highs[0]:.2f}), RSI topo mais baixo ({rsi_at_highs[-1]:.1f} < {rsi_at_highs[0]:.1f})")

            if len(macd_at_highs) >= 2 and macd_at_highs[-1] < macd_at_highs[0]:
                bearish_macd = True
                details.append(f"Divergência baixista MACD: preço topo mais alto ({price_highs[-1]:.2f} > {price_highs[0]:.2f}), histograma topo mais baixo ({macd_at_highs[-1]:.5f} < {macd_at_highs[0]:.5f})")

    # Check bullish divergence (price lower low, indicator higher low)
    if len(recent_lows) >= 2:
        price_lows = [l[1] for l in recent_lows[-2:]]
        if price_lows[-1] < price_lows[0]:
            # Price made lower low
            rsi_at_lows = [rsi_last5[min(l[0], len(rsi_last5)-1)] for l in recent_lows[-2:]]
            macd_at_lows = [macd_last5[min(l[0], len(macd_last5)-1)] for l in recent_lows[-2:]]

            if len(rsi_at_lows) >= 2 and rsi_at_lows[-1] > rsi_at_lows[0]:
                bullish_rsi = True
                details.append(f"Divergência altista RSI: preço fundo mais baixo ({price_lows[-1]:.2f} < {price_lows[0]:.2f}), RSI fundo mais alto ({rsi_at_lows[-1]:.1f} > {rsi_at_lows[0]:.1f})")

            if len(macd_at_lows) >= 2 and macd_at_lows[-1] > macd_at_lows[0]:
                bullish_macd = True
                details.append(f"Divergência altista MACD: preço fundo mais baixo ({price_lows[-1]:.2f} < {price_lows[0]:.2f}), histograma fundo mais alto ({macd_at_lows[-1]:.5f} > {macd_at_lows[0]:.5f})")

    return {
        "bearish_rsi_divergence": bearish_rsi,
        "bullish_rsi_divergence": bullish_rsi,
        "bearish_macd_divergence": bearish_macd,
        "bullish_macd_divergence": bullish_macd,
        "details": "; ".join(details) if details else "Nenhuma divergência detectada"
    }


def detect_candlestick_patterns(candles: list[dict]) -> list[dict]:
    """Detect candlestick patterns in the last 2-3 candles.
    Returns list of detected patterns with direction."""
    if len(candles) < 2:
        return []

    patterns = []
    last_idx = len(candles) - 1

    def get_body_size(candle):
        open_p = float(candle["open"])
        close_p = float(candle["close"])
        return abs(close_p - open_p)

    def get_upper_wick(candle):
        open_p = float(candle["open"])
        close_p = float(candle["close"])
        high = float(candle["high"])
        return high - max(open_p, close_p)

    def get_lower_wick(candle):
        open_p = float(candle["open"])
        close_p = float(candle["close"])
        low = float(candle["low"])
        return min(open_p, close_p) - low

    def is_bullish(candle):
        return float(candle["close"]) > float(candle["open"])

    def is_bearish(candle):
        return float(candle["close"]) < float(candle["open"])

    # Need at least 2 candles for engulfing, 3 for some patterns
    for i in range(max(0, last_idx - 2), last_idx):
        current = candles[i]
        prev = candles[i - 1] if i > 0 else None

        curr_body = get_body_size(current)
        curr_open = float(current["open"])
        curr_close = float(current["close"])
        curr_high = float(current["high"])
        curr_low = float(current["low"])
        atr_estimate = curr_high - curr_low

        if prev:
            prev_body = get_body_size(prev)
            prev_open = float(prev["open"])
            prev_close = float(prev["close"])
            prev_high = float(prev["high"])
            prev_low = float(prev["low"])

            # Bullish Engulfing
            if (is_bearish(prev) and is_bullish(current) and
                curr_body > prev_body and
                curr_open <= prev_close and curr_close >= prev_open):
                patterns.append({
                    "pattern": "bullish_engulfing",
                    "direction": "bullish",
                    "candle_idx": i,
                    "description": "Engolfo de alta: vela de alta engolfa vela de baixa anterior"
                })

            # Bearish Engulfing
            if (is_bullish(prev) and is_bearish(current) and
                curr_body > prev_body and
                curr_open >= prev_close and curr_close <= prev_open):
                patterns.append({
                    "pattern": "bearish_engulfing",
                    "direction": "bearish",
                    "candle_idx": i,
                    "description": "Engolfo de baixa: vela de baixa engolfa vela de alta anterior"
                })

        # Hammer (at bottom of move, small body, long lower wick)
        lower_wick = get_lower_wick(current)
        upper_wick = get_upper_wick(current)
        if (curr_body < atr_estimate * 0.3 and
            lower_wick > curr_body * 2 and
            upper_wick < curr_body * 0.5):
            patterns.append({
                "pattern": "hammer",
                "direction": "bullish",
                "candle_idx": i,
                "description": "Martelo: corpo pequeno com pavio inferior longo (sinal de reversão altista)"
            })

        # Shooting Star (at top of move, small body, long upper wick)
        if (curr_body < atr_estimate * 0.3 and
            upper_wick > curr_body * 2 and
            lower_wick < curr_body * 0.5):
            patterns.append({
                "pattern": "shooting_star",
                "direction": "bearish",
                "candle_idx": i,
                "description": "Estrela cadente: corpo pequeno com pavio superior longo (sinal de reversão baixista)"
            })

        # Doji (open ≈ close)
        if curr_body < atr_estimate * 0.1:
            patterns.append({
                "pattern": "doji",
                "direction": "neutral",
                "candle_idx": i,
                "description": "Doji: abertura e fechamento muito próximos (indecisão do mercado)"
            })

    return patterns


def detect_sr_zones(candles: list[dict], atr: float) -> list[dict]:
    """Detect support and resistance zones from price history.
    Returns top 3-5 zones sorted by reaction count."""
    if len(candles) < 20:
        return []

    df = pd.DataFrame(candles)
    for col in ("open", "high", "low", "close"):
        df.loc[:, col] = df[col].astype(float)

    # Find local highs and lows
    highs = []
    lows = []

    for i in range(2, len(df) - 2):
        # Local high
        if (df.iloc[i]["high"] > df.iloc[i-1]["high"] and
            df.iloc[i]["high"] > df.iloc[i-2]["high"] and
            df.iloc[i]["high"] > df.iloc[i+1]["high"] and
            df.iloc[i]["high"] > df.iloc[i+2]["high"]):
            highs.append(df.iloc[i]["high"])

        # Local low
        if (df.iloc[i]["low"] < df.iloc[i-1]["low"] and
            df.iloc[i]["low"] < df.iloc[i-2]["low"] and
            df.iloc[i]["low"] < df.iloc[i+1]["low"] and
            df.iloc[i]["low"] < df.iloc[i+2]["low"]):
            lows.append(df.iloc[i]["low"])

    # Cluster nearby levels into zones
    zone_size = max(atr * 0.5, df["close"].iloc[-1] * 0.001)  # Minimum 0.1% of price

    def cluster_levels(levels):
        if not levels:
            return []
        levels_sorted = sorted(levels)
        clusters = []
        current_cluster = [levels_sorted[0]]

        for level in levels_sorted[1:]:
            if level - current_cluster[0] <= zone_size:
                current_cluster.append(level)
            else:
                clusters.append(current_cluster)
                current_cluster = [level]

        if current_cluster:
            clusters.append(current_cluster)

        # Count reactions per cluster (how many times price touched this zone)
        zones = []
        for cluster in clusters:
            zone_low = min(cluster)
            zone_high = max(cluster)
            zone_mid = (zone_low + zone_high) / 2

            # Count how many candles had high/low in this zone
            reactions = 0
            for _, candle in df.iterrows():
                high = candle["high"]
                low = candle["low"]
                if zone_low <= high <= zone_high or zone_low <= low <= zone_high:
                    reactions += 1

            zones.append({
                "low": zone_low,
                "high": zone_high,
                "mid": zone_mid,
                "reactions": reactions
            })

        return zones

    resistance_zones = cluster_levels(highs)
    support_zones = cluster_levels(lows)

    # Convert to list and add type
    result = []
    for z in resistance_zones:
        result.append({
            "type": "resistance",
            "low": round(z["low"], 5),
            "high": round(z["high"], 5),
            "reactions": z["reactions"]
        })

    for z in support_zones:
        result.append({
            "type": "support",
            "low": round(z["low"], 5),
            "high": round(z["high"], 5),
            "reactions": z["reactions"]
        })

    # Sort by reaction count and return top 5
    result.sort(key=lambda x: x["reactions"], reverse=True)
    return result[:5]
