from datetime import datetime, timezone

from sqlalchemy import Integer, Float, String, Boolean, Text, JSON, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from typing import Optional, Any

from app.db.connection import Base


class BotConfig(Base):
    __tablename__ = "bot_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    value: Mapped[dict[str, Any] | list | str | int | float | bool | None] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<BotConfig(id={self.id}, key='{self.key}')>"


class PromptVersion(Base):
    __tablename__ = "prompt_version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    note: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<PromptVersion(id={self.id}, is_active={self.is_active}, created_at='{self.created_at}')>"


class IndicatorConfig(Base):
    __tablename__ = "indicator_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    indicator_type: Mapped[str] = mapped_column(String, nullable=False)
    parameters: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<IndicatorConfig(id={self.id}, name='{self.name}', type='{self.indicator_type}')>"


class Candle(Base):
    __tablename__ = "candle"
    __table_args__ = (
        UniqueConstraint("symbol", "timeframe", "epoch", name="uq_candle_symbol_timeframe_epoch"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    timeframe: Mapped[str] = mapped_column(String, nullable=False)
    epoch: Mapped[int] = mapped_column(Integer, nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<Candle(id={self.id}, symbol='{self.symbol}', timeframe='{self.timeframe}', epoch={self.epoch})>"


class Signal(Base):
    __tablename__ = "signal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    timeframe: Mapped[str] = mapped_column(String, nullable=False)
    direction: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    entry_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    exit_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    outcome: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    duration: Mapped[int] = mapped_column(Integer, nullable=False)
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Technical indicator fields
    rsi: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bb_position: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    adx: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    atr_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price_vs_ema50: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    macd_line: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    macd_signal: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    macd_histogram: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Context fields
    regime: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    time_window: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    m15_bias: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    strategy: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    confluence_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    entry_candle_time: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<Signal(id={self.id}, symbol='{self.symbol}', direction='{self.direction}', status='{self.status}')>"


class AgentCycle(Base):
    __tablename__ = "agent_cycle"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cycle_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    symbol: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    regime: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    m15_bias: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    time_window: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    confluence_call: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    confluence_put: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    llm_direction: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    llm_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    llm_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    llm_raw_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    emitted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    signal_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    skip_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    def __repr__(self) -> str:
        return f"<AgentCycle(id={self.id}, cycle={self.cycle_number}, dir={self.llm_direction})>"


class AgentLesson(Base):
    __tablename__ = "agent_lesson"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str] = mapped_column(String, nullable=False, index=True)
    sample_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    last_reinforced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reflection_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<AgentLesson(id={self.id}, topic='{self.topic}', active={self.is_active})>"


class AgentReflection(Base):
    __tablename__ = "agent_reflection"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    cycles_analyzed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    trigger: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    raw_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<AgentReflection(id={self.id}, trigger={self.trigger})>"
