import pytest
from app.indicators.service import IndicatorService
from app.db.models import IndicatorConfig


SAMPLE_CANDLES = [
    {"time": 1000 + i * 60, "open": 100.0 + i * 0.5, "high": 101.0 + i * 0.5,
     "low": 99.0 + i * 0.5, "close": 100.5 + i * 0.5}
    for i in range(60)
]


def test_analyze_with_defaults():
    result = IndicatorService.analyze_with_config(SAMPLE_CANDLES, [])
    assert "rsi" in result
    assert "last_close" in result


def test_build_indicator_params_from_db():
    configs = [
        IndicatorConfig(name="RSI_14", indicator_type="RSI",
                        parameters={"period": 14}, enabled=True),
        IndicatorConfig(name="MACD_default", indicator_type="MACD",
                        parameters={"fast": 12, "slow": 26, "signal": 9}, enabled=False),
    ]
    params = IndicatorService.build_params_from_configs(configs)
    assert params["rsi"]["period"] == 14
    assert "macd" not in params  # disabled


def test_analyze_with_partial_configs():
    configs = [
        IndicatorConfig(name="RSI_14", indicator_type="RSI",
                        parameters={"period": 14}, enabled=True),
    ]
    result = IndicatorService.analyze_with_config(SAMPLE_CANDLES, configs)
    assert "rsi" in result
    assert "macd" not in result  # not configured
