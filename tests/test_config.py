import pytest
from app.config import Settings, DEFAULT_INDICATORS, DEFAULT_BOT_CONFIG


def test_settings_defaults():
    s = Settings(database_url="postgresql+asyncpg://test:test@localhost/test")
    assert s.database_url == "postgresql+asyncpg://test:test@localhost/test"
    assert s.deriv_app_id == "1089"


def test_default_indicators_structure():
    assert len(DEFAULT_INDICATORS) == 6
    types = {ind["indicator_type"] for ind in DEFAULT_INDICATORS}
    assert types == {"RSI", "MACD", "BB", "EMA", "ADX", "ATR"}


def test_default_bot_config_keys():
    expected = {"symbol", "decision_timeframe", "context_timeframe", "loop_interval",
                "duration", "min_confidence", "model", "candle_settle_delay", "candles_count"}
    assert set(DEFAULT_BOT_CONFIG.keys()) == expected
