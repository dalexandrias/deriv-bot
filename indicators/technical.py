import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, ADXIndicator
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
    }
