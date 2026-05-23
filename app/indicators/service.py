from app.indicators.technical import analyze as _analyze_default


class IndicatorService:
    @staticmethod
    def analyze_with_config(candles: list[dict], indicator_configs: list) -> dict:
        """Analyze candles using indicator configs from DB.

        If configs is empty, falls back to default hardcoded parameters
        (same as the original analyze() function).
        """
        if not indicator_configs:
            return _analyze_default(candles)

        import pandas as pd
        from ta.momentum import RSIIndicator
        from ta.trend import EMAIndicator, ADXIndicator, MACD
        from ta.volatility import BollingerBands, AverageTrueRange

        params = IndicatorService.build_params_from_configs(indicator_configs)

        df = pd.DataFrame(candles)
        for col in ("open", "high", "low", "close"):
            df.loc[:, col] = df[col].astype(float)
        close = df["close"]
        last_close = float(close.iloc[-1])

        result = {"last_close": round(last_close, 5), "candles_count": len(candles)}

        if "rsi" in params:
            p = params["rsi"]["period"]
            series = RSIIndicator(close=close, window=p).rsi()
            rsi = float(series.iloc[-1]) if not series.empty else float("nan")
            result["rsi"] = round(rsi, 2)

        if "bb" in params:
            p = params["bb"]["period"]
            sd = params["bb"]["std_dev"]
            bb = BollingerBands(close=close, window=p, window_dev=sd)
            result["bb_upper"] = round(float(bb.bollinger_hband().iloc[-1]), 5)
            result["bb_lower"] = round(float(bb.bollinger_lband().iloc[-1]), 5)
            result["bb_position"] = "acima" if last_close > result["bb_upper"] else (
                "abaixo" if last_close < result["bb_lower"] else "dentro")

        if "ema" in params:
            p = params["ema"]["period"]
            ema_val = float(EMAIndicator(close=close, window=p).ema_indicator().iloc[-1])
            result["ema50"] = round(ema_val, 5)
            result["price_vs_ema50"] = "acima" if last_close > ema_val else "abaixo"

        if "adx" in params:
            p = params["adx"]["period"]
            try:
                adx = float(ADXIndicator(high=df["high"], low=df["low"], close=close, window=p).adx().dropna().iloc[-1])
            except Exception:
                adx = float("nan")
            result["adx"] = round(adx, 2)

        if "atr" in params:
            p = params["atr"]["period"]
            atr = float(AverageTrueRange(high=df["high"], low=df["low"], close=close, window=p).average_true_range().iloc[-1])
            result["atr"] = round(atr, 5)
            result["atr_pct"] = round(atr / last_close * 100, 2) if last_close else 0.0

        if "macd" in params:
            f, s, sig = params["macd"]["fast"], params["macd"]["slow"], params["macd"]["signal"]
            obj = MACD(close=close, window_fast=f, window_slow=s, window_sign=sig)
            result["macd_line"] = round(float(obj.macd().dropna().iloc[-1]), 5)
            result["macd_signal"] = round(float(obj.macd_signal().dropna().iloc[-1]), 5)
            result["macd_histogram"] = round(float(obj.macd_diff().dropna().iloc[-1]), 5)

        return result

    @staticmethod
    def build_params_from_configs(configs: list) -> dict:
        """Convert a list of IndicatorConfig ORM objects into a params dict."""
        type_map = {
            "RSI": "rsi", "MACD": "macd", "BB": "bb",
            "EMA": "ema", "ADX": "adx", "ATR": "atr",
        }
        params = {}
        for cfg in configs:
            if not cfg.enabled:
                continue
            key = type_map.get(cfg.indicator_type)
            if key:
                params[key] = cfg.parameters
        return params
