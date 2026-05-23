from datetime import datetime, timezone

import pytest
from sqlalchemy import select, inspect
from sqlalchemy.exc import IntegrityError

from app.db.models import Base, BotConfig, IndicatorConfig, Candle, Signal


class TestTablesExist:
    """Verify all 4 tables are created after create_all."""

    async def test_bot_config_table_exists(self, engine):
        async with engine.begin() as conn:
            def check(inspector):
                return "bot_config" in inspector.get_table_names()
            result = await conn.run_sync(lambda c: check(inspect(c)))
        assert result is True

    async def test_indicator_config_table_exists(self, engine):
        async with engine.begin() as conn:
            def check(inspector):
                return "indicator_config" in inspector.get_table_names()
            result = await conn.run_sync(lambda c: check(inspect(c)))
        assert result is True

    async def test_candle_table_exists(self, engine):
        async with engine.begin() as conn:
            def check(inspector):
                return "candle" in inspector.get_table_names()
            result = await conn.run_sync(lambda c: check(inspect(c)))
        assert result is True

    async def test_signal_table_exists(self, engine):
        async with engine.begin() as conn:
            def check(inspector):
                return "signal" in inspector.get_table_names()
            result = await conn.run_sync(lambda c: check(inspect(c)))
        assert result is True


class TestBotConfigCRUD:
    """CRUD operations for bot_config table."""

    async def test_create_bot_config(self, db_session):
        config = BotConfig(key="max_concurrent_trades", value=5)
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        assert config.id is not None
        assert config.key == "max_concurrent_trades"
        assert config.value == 5
        assert config.updated_at is not None

    async def test_read_bot_config(self, db_session):
        config = BotConfig(key="risk_per_trade", value=2.0)
        db_session.add(config)
        await db_session.commit()

        result = await db_session.execute(
            select(BotConfig).where(BotConfig.key == "risk_per_trade")
        )
        fetched = result.scalar_one()

        assert fetched.key == "risk_per_trade"
        assert fetched.value == 2.0

    async def test_update_bot_config(self, db_session):
        config = BotConfig(key="take_profit_pct", value=10)
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        config.value = 15
        await db_session.commit()
        await db_session.refresh(config)

        assert config.value == 15

    async def test_delete_bot_config(self, db_session):
        config = BotConfig(key="temp_setting", value="remove_me")
        db_session.add(config)
        await db_session.commit()
        config_id = config.id

        await db_session.delete(config)
        await db_session.commit()

        result = await db_session.execute(
            select(BotConfig).where(BotConfig.id == config_id)
        )
        assert result.scalar_one_or_none() is None

    async def test_bot_config_json_value(self, db_session):
        config = BotConfig(key="trading_params", value={"pairs": ["EURUSD", "GBPUSD"], "max_spread": 0.5})
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        assert config.value["pairs"] == ["EURUSD", "GBPUSD"]
        assert config.value["max_spread"] == 0.5


class TestIndicatorConfigCRUD:
    """CRUD operations for indicator_config table."""

    async def test_create_indicator_config(self, db_session):
        indicator = IndicatorConfig(
            name="rsi_14",
            indicator_type="RSI",
            parameters={"period": 14, "overbought": 70, "oversold": 30},
            enabled=True,
        )
        db_session.add(indicator)
        await db_session.commit()
        await db_session.refresh(indicator)

        assert indicator.id is not None
        assert indicator.name == "rsi_14"
        assert indicator.indicator_type == "RSI"
        assert indicator.enabled is True
        assert indicator.created_at is not None

    async def test_read_indicator_config(self, db_session):
        indicator = IndicatorConfig(
            name="bollinger_bands",
            indicator_type="BB",
            parameters={"period": 20, "std_dev": 2.0},
        )
        db_session.add(indicator)
        await db_session.commit()

        result = await db_session.execute(
            select(IndicatorConfig).where(IndicatorConfig.name == "bollinger_bands")
        )
        fetched = result.scalar_one()

        assert fetched.indicator_type == "BB"
        assert fetched.parameters["period"] == 20

    async def test_update_indicator_config(self, db_session):
        indicator = IndicatorConfig(
            name="ema_50",
            indicator_type="EMA",
            parameters={"period": 50},
            enabled=True,
        )
        db_session.add(indicator)
        await db_session.commit()
        await db_session.refresh(indicator)

        indicator.enabled = False
        params = dict(indicator.parameters)
        params["period"] = 100
        indicator.parameters = params
        await db_session.commit()
        await db_session.refresh(indicator)

        assert indicator.enabled is False
        assert indicator.parameters["period"] == 100

    async def test_delete_indicator_config(self, db_session):
        indicator = IndicatorConfig(
            name="delete_me",
            indicator_type="TEST",
        )
        db_session.add(indicator)
        await db_session.commit()
        indicator_id = indicator.id

        await db_session.delete(indicator)
        await db_session.commit()

        result = await db_session.execute(
            select(IndicatorConfig).where(IndicatorConfig.id == indicator_id)
        )
        assert result.scalar_one_or_none() is None

    async def test_indicator_config_unique_name(self, db_session):
        indicator1 = IndicatorConfig(name="unique_test", indicator_type="TEST")
        db_session.add(indicator1)
        await db_session.commit()

        indicator2 = IndicatorConfig(name="unique_test", indicator_type="OTHER")
        db_session.add(indicator2)

        with pytest.raises(IntegrityError):
            await db_session.commit()


class TestSignalCRUD:
    """CRUD operations for signal table."""

    async def test_create_signal(self, db_session):
        signal = Signal(
            symbol="EURUSD",
            timeframe="M5",
            direction="CALL",
            confidence=0.85,
            status="pending",
            duration=300,
            rsi=55.0,
            bb_position=0.4,
            adx=25.0,
            regime="ranging",
            strategy="rsi_reversal",
            confluence_score=7,
        )
        db_session.add(signal)
        await db_session.commit()
        await db_session.refresh(signal)

        assert signal.id is not None
        assert signal.symbol == "EURUSD"
        assert signal.direction == "CALL"
        assert signal.confidence == 0.85
        assert signal.rsi == 55.0
        assert signal.strategy == "rsi_reversal"
        assert signal.created_at is not None

    async def test_read_signal(self, db_session):
        signal = Signal(
            symbol="GBPUSD",
            timeframe="M1",
            direction="PUT",
            confidence=0.72,
            status="active",
            duration=60,
            reasoning="Bearish divergence on RSI",
        )
        db_session.add(signal)
        await db_session.commit()

        result = await db_session.execute(
            select(Signal).where(Signal.symbol == "GBPUSD")
        )
        fetched = result.scalar_one()

        assert fetched.direction == "PUT"
        assert fetched.reasoning == "Bearish divergence on RSI"

    async def test_update_signal(self, db_session):
        signal = Signal(
            symbol="AUDUSD",
            timeframe="M5",
            direction="CALL",
            confidence=0.8,
            status="pending",
            duration=300,
        )
        db_session.add(signal)
        await db_session.commit()
        await db_session.refresh(signal)

        signal.status = "resolved"
        signal.outcome = "win"
        signal.entry_price = 0.6543
        signal.exit_price = 0.6558
        signal.resolved_at = datetime.now(timezone.utc)
        await db_session.commit()
        await db_session.refresh(signal)

        assert signal.status == "resolved"
        assert signal.outcome == "win"
        assert signal.entry_price == 0.6543
        assert signal.resolved_at is not None

    async def test_delete_signal(self, db_session):
        signal = Signal(
            symbol="USDCAD",
            timeframe="M15",
            direction="PUT",
            confidence=0.6,
            status="pending",
            duration=900,
        )
        db_session.add(signal)
        await db_session.commit()
        signal_id = signal.id

        await db_session.delete(signal)
        await db_session.commit()

        result = await db_session.execute(
            select(Signal).where(Signal.id == signal_id)
        )
        assert result.scalar_one_or_none() is None

    async def test_signal_all_nullable_fields(self, db_session):
        signal = Signal(
            symbol="EURGBP",
            timeframe="M5",
            direction="CALL",
            confidence=0.5,
            status="pending",
            duration=300,
        )
        db_session.add(signal)
        await db_session.commit()
        await db_session.refresh(signal)

        assert signal.entry_price is None
        assert signal.exit_price is None
        assert signal.outcome is None
        assert signal.reasoning is None
        assert signal.rsi is None
        assert signal.regime is None
        assert signal.strategy is None
        assert signal.resolved_at is None


class TestCandleUniqueConstraint:
    """Test unique constraint on candle(symbol, timeframe, epoch)."""

    async def test_insert_duplicate_candle_raises_integrity_error(self, db_session):
        epoch = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        candle1 = Candle(
            symbol="EURUSD",
            timeframe="M5",
            epoch=epoch,
            open=1.0850,
            high=1.0860,
            low=1.0845,
            close=1.0855,
        )
        db_session.add(candle1)
        await db_session.commit()

        candle2 = Candle(
            symbol="EURUSD",
            timeframe="M5",
            epoch=epoch,
            open=1.0851,
            high=1.0861,
            low=1.0846,
            close=1.0856,
        )
        db_session.add(candle2)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_insert_different_candles_succeeds(self, db_session):
        epoch1 = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        epoch2 = datetime(2025, 1, 1, 12, 5, 0, tzinfo=timezone.utc)

        candle1 = Candle(
            symbol="EURUSD",
            timeframe="M5",
            epoch=epoch1,
            open=1.0850,
            high=1.0860,
            low=1.0845,
            close=1.0855,
        )
        candle2 = Candle(
            symbol="EURUSD",
            timeframe="M5",
            epoch=epoch2,
            open=1.0855,
            high=1.0870,
            low=1.0850,
            close=1.0865,
        )
        db_session.add_all([candle1, candle2])
        await db_session.commit()

        result = await db_session.execute(select(Candle))
        candles = result.scalars().all()
        assert len(candles) == 2

    async def test_candle_nullable_volume(self, db_session):
        candle = Candle(
            symbol="EURUSD",
            timeframe="M5",
            epoch=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            open=1.0850,
            high=1.0860,
            low=1.0845,
            close=1.0855,
        )
        db_session.add(candle)
        await db_session.commit()
        await db_session.refresh(candle)

        assert candle.volume is None
