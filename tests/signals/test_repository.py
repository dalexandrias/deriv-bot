import pytest
from datetime import datetime, timezone, timedelta

from app.db.models import Signal as SignalORM
from app.signals.models import SignalCreate
from app.signals.repository import SignalRepository


@pytest.fixture
def repo(db_session):
    return SignalRepository(db_session)


# ---- 1. insert_signal ----

async def test_insert_signal(repo, db_session):
    data = SignalCreate(
        symbol="R_25",
        timeframe="5m",
        direction="CALL",
        confidence=0.8,
        duration=300,
        status="pending",
    )
    signal_id = await repo.insert_signal(data)
    assert signal_id is not None
    assert isinstance(signal_id, int)

    sig = await repo.get_signal_by_id(signal_id)
    assert sig is not None
    assert sig.symbol == "R_25"
    assert sig.direction == "CALL"
    assert sig.confidence == 0.8
    assert sig.status == "pending"


# ---- 2. update_outcome ----

async def test_update_outcome(repo):
    data = SignalCreate(symbol="R_25", timeframe="5m", direction="PUT", duration=300)
    signal_id = await repo.insert_signal(data)

    await repo.update_outcome(signal_id, entry_price=100.5, exit_price=102.3, outcome="win")

    sig = await repo.get_signal_by_id(signal_id)
    assert sig is not None
    assert sig.entry_price == 100.5
    assert sig.exit_price == 102.3
    assert sig.outcome == "win"
    assert sig.status == "resolved"
    assert sig.resolved_at is not None


# ---- 3. get_signals_filtered ----

async def test_get_signals_filtered(repo):
    await repo.insert_signal(
        SignalCreate(symbol="R_25", timeframe="5m", direction="CALL", duration=300)
    )
    await repo.insert_signal(
        SignalCreate(symbol="R_25", timeframe="5m", direction="PUT", duration=300)
    )

    # filter by direction=CALL
    results = await repo.get_signals_filtered(direction="CALL")
    assert len(results) == 1
    assert results[0]["direction"] == "CALL"


# ---- 4. get_stats_empty ----

async def test_get_stats_empty(repo):
    stats = await repo.get_overall_stats()
    assert stats["total"] == 0
    assert stats["wins"] == 0
    assert stats["losses"] == 0
    assert stats["win_rate"] == 0.0


# ---- 5. get_stats_with_data ----

async def test_get_stats_with_data(repo):
    # Insert 3 signals and resolve them: win, loss, win
    id1 = await repo.insert_signal(
        SignalCreate(symbol="R_25", timeframe="5m", direction="CALL", duration=300, confidence=0.7)
    )
    id2 = await repo.insert_signal(
        SignalCreate(symbol="R_25", timeframe="5m", direction="PUT", duration=300, confidence=0.6)
    )
    id3 = await repo.insert_signal(
        SignalCreate(symbol="R_25", timeframe="5m", direction="CALL", duration=300, confidence=0.8)
    )

    await repo.update_outcome(id1, entry_price=100.0, exit_price=101.5, outcome="win")
    await repo.update_outcome(id2, entry_price=100.0, exit_price=99.0, outcome="loss")
    await repo.update_outcome(id3, entry_price=100.0, exit_price=101.0, outcome="win")

    stats = await repo.get_overall_stats()
    assert stats["total"] == 3
    assert stats["wins"] == 2
    assert stats["losses"] == 1
    assert stats["win_rate"] == 0.67
    assert stats["avg_confidence"] == round((0.7 + 0.6 + 0.8) / 3, 2)
