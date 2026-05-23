from pydantic import BaseModel


class BotConfigUpdate(BaseModel):
    configs: dict[str, object]


class IndicatorCreate(BaseModel):
    name: str
    indicator_type: str
    parameters: dict
    enabled: bool = True


class IndicatorUpdate(BaseModel):
    parameters: dict | None = None
    enabled: bool | None = None


class CollectorConfigUpdate(BaseModel):
    symbols: list[str] | None = None
    timeframes: list[str] | None = None
