import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator
from ta.volatility import BollingerBands


def analyze(candles: list[dict]) -> dict:
    if not candles:
        raise ValueError("Lista de candles vazia")

    df = pd.DataFrame(candles)
    for col in ("open", "high", "low", "close"):
        df.loc[:, col] = df[col].astype(float)

    close = df["close"]

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

    macd_obj = MACD(close=close)
    macd_line = macd_obj.macd().iloc[-1]
    macd_sig_line = macd_obj.macd_signal().iloc[-1]
    macd_val = float(macd_line) if not pd.isna(macd_line) else 0.0
    macd_signal = "compra" if macd_line > macd_sig_line else "venda"

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

    sma_short = SMAIndicator(close=close, window=min(5, len(close))).sma_indicator().iloc[-1]
    sma_long_window = min(20, len(close))
    sma_long = SMAIndicator(close=close, window=sma_long_window).sma_indicator().iloc[-1]
    if pd.isna(sma_short) or pd.isna(sma_long):
        trend = "lateral"
    elif sma_short > sma_long * 1.0005:
        trend = "alta"
    elif sma_short < sma_long * 0.9995:
        trend = "baixa"
    else:
        trend = "lateral"

    return {
        "trend": trend,
        "rsi": round(rsi, 2),
        "rsi_signal": rsi_signal,
        "macd": round(macd_val, 6),
        "macd_signal": macd_signal,
        "bb_upper": round(bb_upper, 5),
        "bb_lower": round(bb_lower, 5),
        "bb_position": bb_position,
        "last_close": round(last_close, 5),
        "candles_count": len(candles),
    }
