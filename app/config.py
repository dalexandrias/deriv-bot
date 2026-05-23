from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    database_url: str = Field(default="postgresql+asyncpg://localhost/deriv")
    deriv_api_token: str = Field(default="")
    deriv_app_id: str = Field(default="1089")
    openrouter_api_key: str = Field(default="")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


DEFAULT_BOT_CONFIG = {
    "symbol": "R_25",
    "decision_timeframe": "5m",
    "context_timeframe": "15m",
    "loop_interval": 300,
    "duration": 300,
    "min_confidence": 0.50,
    "model": "deepseek/deepseek-v4-flash",
    "candle_settle_delay": 2,
    "candles_count": 60,
}

DEFAULT_INDICATORS = [
    {"name": "RSI_14", "indicator_type": "RSI", "parameters": {"period": 14}, "enabled": True},
    {"name": "MACD_default", "indicator_type": "MACD", "parameters": {"fast": 12, "slow": 26, "signal": 9}, "enabled": True},
    {"name": "BB_20_2", "indicator_type": "BB", "parameters": {"period": 20, "std_dev": 2}, "enabled": True},
    {"name": "EMA_50", "indicator_type": "EMA", "parameters": {"period": 50}, "enabled": True},
    {"name": "ADX_14", "indicator_type": "ADX", "parameters": {"period": 14}, "enabled": True},
    {"name": "ATR_14", "indicator_type": "ATR", "parameters": {"period": 14}, "enabled": True},
]


settings = Settings()
