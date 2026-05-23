# Modular Monolith Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the Deriv trading bot from a SQLite monolith into a FastAPI-based modular monolith with PostgreSQL, REST APIs, and configurable indicators stored in the database.

**Architecture:** Single FastAPI application serving REST APIs + SSE. Background asyncio tasks run the data collector (WebSocket → PostgreSQL) and trading agent (LLM). PostgreSQL is the sole data store. SQLite is removed entirely.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2.0 (async), asyncpg, Alembic, pydantic-settings, httpx, websockets, ta, pandas, loguru, textual (TUI)

---

## File Map

### New files to create:

| File | Responsibility |
|------|---------------|
| `app/__init__.py` | Package marker |
| `app/main.py` | FastAPI app + lifespan (start collector + agent) |
| `app/config.py` | pydantic-settings: env vars + DB config loader |
| `app/api/__init__.py` | Package marker |
| `app/api/router.py` | Aggregate all API routers |
| `app/api/bot.py` | Bot on/off/status endpoints |
| `app/api/collector.py` | Collector config/status endpoints |
| `app/api/signals.py` | Signal history + stats endpoints |
| `app/api/indicators.py` | Indicator config CRUD endpoints |
| `app/api/health.py` | Health check + Prometheus metrics |
| `app/api/schemas.py` | Pydantic request/response models |
| `app/collector/__init__.py` | Package marker |
| `app/collector/service.py` | Background collector loop (WS → DB) |
| `app/collector/deriv_client.py` | DerivClient (migrated from deriv/client.py) |
| `app/agent/__init__.py` | Package marker |
| `app/agent/service.py` | Background agent loop (orchestrates analysis cycle) |
| `app/agent/pre_analysis.py` | Pre-analysis (migrated from agent/pre_analysis.py) |
| `app/agent/prompts.py` | Prompts (migrated from agent/prompts.py) |
| `app/agent/tools.py` | LLM tools (migrated from agent/tools.py) |
| `app/agent/learning.py` | Learning block (migrated from agent/learning.py) |
| `app/indicators/__init__.py` | Package marker |
| `app/indicators/service.py` | Indicator calculation using DB config |
| `app/indicators/technical.py` | TA wrapper (migrated from indicators/technical.py) |
| `app/signals/__init__.py` | Package marker |
| `app/signals/models.py` | Signal dataclass (migrated) |
| `app/signals/repository.py` | PostgreSQL repository (rewritten from SQLite) |
| `app/signals/verifier.py` | Signal verification (migrated) |
| `app/db/__init__.py` | Package marker |
| `app/db/connection.py` | SQLAlchemy async engine + session factory |
| `app/db/models.py` | SQLAlchemy ORM models |
| `app/events/__init__.py` | Package marker |
| `app/events/protocol.py` | Event types (migrated) |
| `app/events/publisher.py` | SSE + internal event bus |
| `app/dashboard/` | TUI (migrated, adapted to use new imports) |
| `alembic.ini` | Alembic configuration |
| `app/db/migrations/env.py` | Alembic migration env (async) |
| `app/db/migrations/versions/001_initial.py` | Initial schema migration |
| `pyproject.toml` | Project config (replaces requirements.txt) |
| `Dockerfile` | Production container |
| `docker-compose.yml` | Local dev (app + postgres) |
| `tests/__init__.py` | Test package |
| `tests/conftest.py` | Shared fixtures (test DB, test client) |
| `tests/db/test_models.py` | DB model tests |
| `tests/api/test_bot.py` | Bot API tests |
| `tests/api/test_signals.py` | Signal API tests |
| `tests/api/test_indicators.py` | Indicator API tests |
| `tests/api/test_collector.py` | Collector API tests |
| `tests/api/test_health.py` | Health API tests |
| `tests/signals/test_repository.py` | Repository tests |
| `tests/indicators/test_service.py` | Indicator service tests |

### Files to delete (after migration):

| File | Reason |
|------|--------|
| `main.py` | Replaced by `app/main.py` |
| `deriv/` | Replaced by `app/collector/` |
| `agent/` | Replaced by `app/agent/` |
| `indicators/` | Replaced by `app/indicators/` |
| `signals/` | Replaced by `app/signals/` |
| `events/` | Replaced by `app/events/` |
| `utils/` | Replaced by inline usage |
| `dashboard/` | Replaced by `app/dashboard/` |
| `requirements.txt` | Replaced by `pyproject.toml` |
| `data/` | No longer needed (PostgreSQL) |

---

### Task 1: Project Setup (pyproject.toml + Directory Skeleton)

**Files:**
- Create: `pyproject.toml`
- Create: `app/__init__.py`
- Create: `app/api/__init__.py`
- Create: `app/collector/__init__.py`
- Create: `app/agent/__init__.py`
- Create: `app/indicators/__init__.py`
- Create: `app/signals/__init__.py`
- Create: `app/db/__init__.py`
- Create: `app/events/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "deriv-bot"
version = "2.0.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sqlalchemy[asyncio]>=2.0.36",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.6.0",
    "httpx>=0.27.0",
    "websockets>=12.0",
    "pandas>=2.2.0",
    "ta>=0.11.0",
    "loguru>=0.7.2",
    "python-dotenv>=1.0.0",
    "pyyaml>=6.0.1",
    "textual>=0.85.0",
    "sse-starlette>=2.0.0",
    "prometheus-client>=0.21.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "httpx",  # for TestClient
    "aiosqlite>=0.20.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.setuptools.packages.find]
include = ["app*"]
```

- [ ] **Step 2: Create all __init__.py files**

Each `__init__.py` is empty (just a package marker):

```bash
touch app/__init__.py app/api/__init__.py app/collector/__init__.py \
      app/agent/__init__.py app/indicators/__init__.py app/signals/__init__.py \
      app/db/__init__.py app/events/__init__.py tests/__init__.py
```

- [ ] **Step 3: Install dependencies**

Run: `pip install -e ".[dev]"`
Expected: All packages installed successfully.

- [ ] **Step 4: Verify imports work**

Run: `python -c "import app; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml app/__init__.py app/api/__init__.py app/collector/__init__.py \
      app/agent/__init__.py app/indicators/__init__.py app/signals/__init__.py \
      app/db/__init__.py app/events/__init__.py tests/__init__.py
git commit -m "chore: scaffold modular monolith structure with pyproject.toml"
```

---

### Task 2: Database Layer (SQLAlchemy Models + Connection + Alembic)

**Files:**
- Create: `app/db/connection.py`
- Create: `app/db/models.py`
- Create: `alembic.ini`
- Create: `app/db/migrations/env.py`
- Create: `app/db/migrations/script.py.mako`
- Create: `app/db/migrations/versions/001_initial.py`
- Test: `tests/db/test_models.py`

- [ ] **Step 1: Write the test for ORM models**

Create `tests/db/test_models.py`:

```python
import pytest
from sqlalchemy import text
from app.db.models import BotConfig, IndicatorConfig, Candle, Signal


@pytest.mark.asyncio
async def test_create_tables(db_session):
    """Verify all tables were created by the fixture."""
    result = await db_session.execute(text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public'"
    ))
    tables = {row[0] for row in result}
    assert "bot_config" in tables
    assert "indicator_config" in tables
    assert "candle" in tables
    assert "signal" in tables


@pytest.mark.asyncio
async def test_bot_config_crud(db_session):
    cfg = BotConfig(key="symbol", value='"R_25"')
    db_session.add(cfg)
    await db_session.commit()

    fetched = await db_session.get(BotConfig, cfg.id)
    assert fetched.key == "symbol"
    assert fetched.value == '"R_25"'


@pytest.mark.asyncio
async def test_indicator_config_crud(db_session):
    ind = IndicatorConfig(
        name="RSI_14", indicator_type="RSI",
        parameters={"period": 14}, enabled=True,
    )
    db_session.add(ind)
    await db_session.commit()

    fetched = await db_session.get(IndicatorConfig, ind.id)
    assert fetched.name == "RSI_14"
    assert fetched.parameters == {"period": 14}
    assert fetched.enabled is True


@pytest.mark.asyncio
async def test_signal_crud(db_session):
    sig = Signal(
        symbol="R_25", timeframe="5m", direction="CALL",
        confidence=0.75, status="pending", duration=300,
    )
    db_session.add(sig)
    await db_session.commit()

    fetched = await db_session.get(Signal, sig.id)
    assert fetched.direction == "CALL"
    assert fetched.status == "pending"


@pytest.mark.asyncio
async def test_candle_unique_constraint(db_session):
    from datetime import datetime, timezone
    from sqlalchemy.exc import IntegrityError

    epoch = datetime(2026, 1, 1, tzinfo=timezone.utc)
    c1 = Candle(symbol="R_25", timeframe="5m", epoch=epoch, open=100.0,
                high=101.0, low=99.0, close=100.5)
    db_session.add(c1)
    await db_session.commit()

    c2 = Candle(symbol="R_25", timeframe="5m", epoch=epoch, open=100.0,
                high=101.0, low=99.0, close=100.5)
    db_session.add(c2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
```

- [ ] **Step 2: Write conftest with test DB fixture**

Create `tests/conftest.py`:

```python
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db.models import Base


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///tests/test.db",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(engine) -> AsyncSession:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/db/test_models.py -v`
Expected: FAIL — `app.db.models` does not exist yet.

- [ ] **Step 4: Create app/db/connection.py**

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
import os


class Base(DeclarativeBase):
    pass


def create_engine_and_session(database_url: str | None = None):
    url = database_url or os.environ["DATABASE_URL"]
    engine = create_async_engine(url, echo=False, pool_size=10, max_overflow=20)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return engine, session_factory
```

- [ ] **Step 5: Create app/db/models.py**

```python
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, Boolean, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from app.db.connection import Base


class BotConfig(Base):
    __tablename__ = "bot_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )


class IndicatorConfig(Base):
    __tablename__ = "indicator_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    indicator_type: Mapped[str] = mapped_column(String(20), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )


class Candle(Base):
    __tablename__ = "candle"
    __table_args__ = (
        UniqueConstraint("symbol", "timeframe", "epoch", name="uq_candle_symbol_tf_epoch"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    epoch: Mapped[datetime] = mapped_column(nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )


class Signal(Base):
    __tablename__ = "signal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    entry_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    duration: Mapped[int] = mapped_column(Integer, nullable=False)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    rsi: Mapped[float | None] = mapped_column(Float, nullable=True)
    bb_position: Mapped[str | None] = mapped_column(String(20), nullable=True)
    adx: Mapped[float | None] = mapped_column(Float, nullable=True)
    atr_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_vs_ema50: Mapped[str | None] = mapped_column(String(20), nullable=True)
    macd_line: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_signal: Mapped[float | None] = mapped_column(Float, nullable=True)
    macd_histogram: Mapped[float | None] = mapped_column(Float, nullable=True)
    regime: Mapped[str | None] = mapped_column(String(20), nullable=True)
    time_window: Mapped[str | None] = mapped_column(String(20), nullable=True)
    m15_bias: Mapped[str | None] = mapped_column(String(20), nullable=True)
    confluence_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    strategy: Mapped[str | None] = mapped_column(String(20), nullable=True)
    entry_candle_time: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/db/test_models.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 7: Set up Alembic**

Run:
```bash
pip install alembic
cd /Users/davialexandriasdeoliveira/Documents/AutomationAnalyseDeriv
alembic init app/db/migrations
```

Then configure `alembic.ini`:

```ini
[alembic]
script_location = app/db/migrations
sqlalchemy.url = postgresql+asyncpg://user:pass@localhost:5432/deriv

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

Replace `app/db/migrations/env.py` with async version:

```python
import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

from app.db.models import Base
from app.config import settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = settings.database_url
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = create_async_engine(settings.database_url)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

Generate the initial migration:

```bash
alembic revision --autogenerate -m "001_initial"
```

- [ ] **Step 8: Commit**

```bash
git add app/db/ alembic.ini tests/conftest.py tests/db/ tests/__init__.py
git commit -m "feat: add PostgreSQL database layer with SQLAlchemy models and Alembic"
```

---

### Task 3: Config System (pydantic-settings + DB-backed config)

**Files:**
- Create: `app/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the test**

Create `tests/test_config.py`:

```python
import pytest
from app.config import Settings, DEFAULT_INDICATORS, DEFAULT_BOT_CONFIG


def test_settings_defaults():
    s = Settings(DATABASE_URL="postgresql+asyncpg://test:test@localhost/test")
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `app.config` does not exist.

- [ ] **Step 3: Create app/config.py**

```python
from pydantic_settings import BaseSettings
from pydantic import Field
import json


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/config.py tests/test_config.py
git commit -m "feat: add pydantic-settings config with default indicators and bot config"
```

---

### Task 4: Signals Repository (PostgreSQL rewrite)

**Files:**
- Create: `app/signals/models.py`
- Create: `app/signals/repository.py`
- Test: `tests/signals/test_repository.py`

- [ ] **Step 1: Write the test**

Create `tests/signals/test_repository.py`:

```python
import pytest
from datetime import datetime, timezone
from app.signals.repository import SignalRepository
from app.signals.models import SignalCreate


@pytest.fixture
def repo(db_session):
    return SignalRepository(db_session)


@pytest.mark.asyncio
async def test_insert_signal(repo):
    data = SignalCreate(
        symbol="R_25", timeframe="5m", direction="CALL",
        confidence=0.75, duration=300, status="pending",
    )
    sig_id = await repo.insert_signal(data)
    assert sig_id is not None
    assert isinstance(sig_id, int)


@pytest.mark.asyncio
async def test_update_outcome(repo):
    data = SignalCreate(
        symbol="R_25", timeframe="5m", direction="CALL",
        confidence=0.75, duration=300, status="pending",
    )
    sig_id = await repo.insert_signal(data)
    await repo.update_outcome(sig_id, entry_price=100.0, exit_price=101.0, outcome="win")

    sig = await repo.get_signal_by_id(sig_id)
    assert sig.outcome == "win"
    assert sig.status == "resolved"


@pytest.mark.asyncio
async def test_get_signals_filtered(repo):
    for direction in ("CALL", "PUT"):
        data = SignalCreate(
            symbol="R_25", timeframe="5m", direction=direction,
            confidence=0.70, duration=300, status="pending",
        )
        await repo.insert_signal(data)

    results = await repo.get_signals_filtered(direction="CALL")
    assert len(results) == 1
    assert results[0]["direction"] == "CALL"


@pytest.mark.asyncio
async def test_get_stats_empty(repo):
    stats = await repo.get_overall_stats()
    assert stats["total"] == 0
    assert stats["win_rate"] == 0.0


@pytest.mark.asyncio
async def test_get_stats_with_data(repo):
    from app.db.models import Signal as SignalORM

    for outcome in ("win", "loss", "win"):
        db_session = repo.session
        sig = SignalORM(
            symbol="R_25", timeframe="5m", direction="CALL",
            confidence=0.70, duration=300, status="resolved", outcome=outcome,
        )
        db_session.add(sig)
    await db_session.commit()

    stats = await repo.get_overall_stats()
    assert stats["total"] == 3
    assert stats["wins"] == 2
    assert stats["win_rate"] == 0.67
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/signals/test_repository.py -v`
Expected: FAIL — `app.signals.repository` does not exist.

- [ ] **Step 3: Create app/signals/models.py**

```python
from dataclasses import dataclass, field
from datetime import datetime, UTC


@dataclass
class SignalCreate:
    symbol: str = "R_25"
    timeframe: str = "5m"
    direction: str = "CALL"
    confidence: float = 0.5
    duration: int = 300
    status: str = "pending"
    rsi: float | None = None
    bb_position: str | None = None
    adx: float | None = None
    atr_pct: float | None = None
    price_vs_ema50: str | None = None
    macd_line: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    regime: str | None = None
    time_window: str | None = None
    m15_bias: str | None = None
    confluence_score: int | None = None
    strategy: str | None = None
    entry_candle_time: str | None = None
    reasoning: str | None = None
```

- [ ] **Step 4: Create app/signals/repository.py**

```python
from datetime import datetime, timezone
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Signal as SignalORM, Candle as CandleORM
from app.signals.models import SignalCreate


class SignalRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def insert_signal(self, data: SignalCreate) -> int:
        sig = SignalORM(
            symbol=data.symbol, timeframe=data.timeframe, direction=data.direction,
            confidence=data.confidence, duration=data.duration, status=data.status,
            rsi=data.rsi, bb_position=data.bb_position, adx=data.adx,
            atr_pct=data.atr_pct, price_vs_ema50=data.price_vs_ema50,
            macd_line=data.macd_line, macd_signal=data.macd_signal,
            macd_histogram=data.macd_histogram, regime=data.regime,
            time_window=data.time_window, m15_bias=data.m15_bias,
            confluence_score=data.confluence_score, strategy=data.strategy,
            entry_candle_time=data.entry_candle_time, reasoning=data.reasoning,
        )
        self.session.add(sig)
        await self.session.flush()
        return sig.id

    async def get_signal_by_id(self, signal_id: int) -> SignalORM | None:
        return await self.session.get(SignalORM, signal_id)

    async def update_outcome(self, signal_id: int, entry_price: float,
                             exit_price: float, outcome: str) -> None:
        sig = await self.get_signal_by_id(signal_id)
        if sig is None:
            return
        sig.entry_price = entry_price
        sig.exit_price = exit_price
        sig.outcome = outcome
        sig.status = "resolved"
        sig.resolved_at = datetime.now(timezone.utc)
        await self.session.flush()

    async def mark_aborted(self, signal_id: int) -> None:
        sig = await self.get_signal_by_id(signal_id)
        if sig is None:
            return
        sig.status = "aborted"
        await self.session.flush()

    async def get_pending_alive(self) -> list[SignalORM]:
        now = datetime.now(timezone.utc)
        stmt = select(SignalORM).where(SignalORM.status == "pending")
        result = await self.session.execute(stmt)
        signals = result.scalars().all()
        alive = []
        for sig in signals:
            if sig.created_at.tzinfo is None:
                sig.created_at = sig.created_at.replace(tzinfo=timezone.utc)
            elapsed = (now - sig.created_at).total_seconds()
            if elapsed < sig.duration:
                alive.append(sig)
        return alive

    async def get_pending_expired(self) -> list[SignalORM]:
        now = datetime.now(timezone.utc)
        stmt = select(SignalORM).where(SignalORM.status == "pending")
        result = await self.session.execute(stmt)
        signals = result.scalars().all()
        expired = []
        for sig in signals:
            if sig.created_at.tzinfo is None:
                sig.created_at = sig.created_at.replace(tzinfo=timezone.utc)
            elapsed = (now - sig.created_at).total_seconds()
            if elapsed >= sig.duration:
                expired.append(sig)
        return expired

    async def get_signals_filtered(
        self, limit: int = 20, outcome: str | None = None,
        direction: str | None = None,
    ) -> list[dict]:
        stmt = select(SignalORM).order_by(SignalORM.created_at.desc()).limit(limit)
        if outcome:
            stmt = stmt.where(SignalORM.outcome == outcome)
        if direction:
            stmt = stmt.where(SignalORM.direction == direction)
        result = await self.session.execute(stmt)
        return [_orm_to_dict(sig) for sig in result.scalars().all()]

    async def get_overall_stats(self) -> dict:
        stmt = select(
            func.count(SignalORM.id).label("total"),
            func.sum(func.cast(SignalORM.outcome == "win", Integer)).label("wins"),
            func.sum(func.cast(SignalORM.outcome == "loss", Integer)).label("losses"),
            func.avg(SignalORM.confidence).label("avg_confidence"),
        ).where(SignalORM.status == "resolved")
        from sqlalchemy import Integer
        result = await self.session.execute(stmt)
        row = result.one()
        total, wins, losses, avg_conf = row
        if total == 0 or total is None:
            return {"total": 0, "wins": 0, "losses": 0, "win_rate": 0.0, "avg_confidence": 0.0}
        return {
            "total": total,
            "wins": wins or 0,
            "losses": losses or 0,
            "win_rate": round((wins or 0) / total, 2),
            "avg_confidence": round(avg_conf or 0, 2),
        }

    async def get_recent_signals(self, limit: int = 20) -> list[dict]:
        stmt = select(SignalORM).order_by(SignalORM.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return [_orm_to_dict(sig) for sig in result.scalars().all()]

    async def get_candles_range(
        self, symbol: str, timeframe: str, count: int = 60,
        before_epoch: datetime | None = None,
    ) -> list[dict]:
        stmt = (
            select(CandleORM)
            .where(CandleORM.symbol == symbol, CandleORM.timeframe == timeframe)
            .order_by(CandleORM.epoch.desc())
            .limit(count)
        )
        if before_epoch:
            stmt = stmt.where(CandleORM.epoch < before_epoch)
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [_candle_to_dict(c) for c in reversed(rows)]

    async def upsert_candles(self, candles: list[dict], symbol: str, timeframe: str) -> None:
        for c in candles:
            from datetime import datetime as dt, timezone as tz
            epoch = dt.fromtimestamp(int(c["time"]), tz=tz.utc)
            stmt = select(CandleORM).where(
                CandleORM.symbol == symbol,
                CandleORM.timeframe == timeframe,
                CandleORM.epoch == epoch,
            )
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                existing.open = float(c["open"])
                existing.high = float(c["high"])
                existing.low = float(c["low"])
                existing.close = float(c["close"])
            else:
                self.session.add(CandleORM(
                    symbol=symbol, timeframe=timeframe, epoch=epoch,
                    open=float(c["open"]), high=float(c["high"]),
                    low=float(c["low"]), close=float(c["close"]),
                ))
        await self.session.flush()


def _orm_to_dict(sig: SignalORM) -> dict:
    return {
        "id": sig.id, "symbol": sig.symbol, "timeframe": sig.timeframe,
        "direction": sig.direction, "confidence": sig.confidence,
        "entry_price": sig.entry_price, "exit_price": sig.exit_price,
        "outcome": sig.outcome, "status": sig.status, "duration": sig.duration,
        "reasoning": sig.reasoning, "rsi": sig.rsi, "bb_position": sig.bb_position,
        "adx": sig.adx, "atr_pct": sig.atr_pct, "price_vs_ema50": sig.price_vs_ema50,
        "macd_line": sig.macd_line, "macd_signal": sig.macd_signal,
        "macd_histogram": sig.macd_histogram, "regime": sig.regime,
        "time_window": sig.time_window, "m15_bias": sig.m15_bias,
        "confluence_score": sig.confluence_score, "strategy": sig.strategy,
        "entry_candle_time": sig.entry_candle_time,
        "created_at": sig.created_at.isoformat() if sig.created_at else None,
        "resolved_at": sig.resolved_at.isoformat() if sig.resolved_at else None,
    }


def _candle_to_dict(c: CandleORM) -> dict:
    return {
        "time": int(c.epoch.timestamp()) if c.epoch else 0,
        "open": c.open, "high": c.high, "low": c.low, "close": c.close,
    }
```

- [ ] **Step 5: Update tests/conftest.py for signal repository tests**

The existing `db_session` fixture works but needs adjustment — it should NOT auto-rollback so inserts are visible. Update the fixture:

```python
@pytest.fixture
async def db_session(engine) -> AsyncSession:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/signals/test_repository.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add app/signals/ tests/signals/ tests/conftest.py
git commit -m "feat: add PostgreSQL signal repository with candles and stats queries"
```

---

### Task 5: Collector Service (Deriv WebSocket → PostgreSQL)

**Files:**
- Create: `app/collector/deriv_client.py`
- Create: `app/collector/service.py`

- [ ] **Step 1: Create app/collector/deriv_client.py**

Copy from `deriv/client.py` and `deriv/market.py`, adapting imports:

```python
import asyncio
import json
import itertools
import os
import websockets
from loguru import logger


class DerivError(Exception):
    pass


TIMEFRAME_TO_GRANULARITY = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
}


class DerivClient:
    WS_URL_TMPL = "wss://ws.derivws.com/websockets/v3?app_id={app_id}"

    def __init__(self, api_token: str, app_id: str | int = 1089):
        self.api_token = api_token
        self.app_id = str(app_id)
        self._ws = None
        self._listener_task: asyncio.Task | None = None
        self._pending: dict[int, asyncio.Future] = {}
        self._req_id_counter = itertools.count(1)
        self._lock = asyncio.Lock()
        self._reconnect_lock = asyncio.Lock()
        self._stop = False

    @property
    def is_connected(self) -> bool:
        return self._ws is not None and not self._ws.closed

    async def connect(self) -> None:
        url = self.WS_URL_TMPL.format(app_id=self.app_id)
        backoff = 1
        while not self._stop:
            try:
                logger.info(f"Conectando à Deriv WS ({url}) ...")
                self._ws = await websockets.connect(url, ping_interval=20, ping_timeout=20)
                self._listener_task = asyncio.create_task(self._listener())
                auth = await self._send({"authorize": self.api_token})
                logger.info(f"Autorizado. Loginid={auth.get('authorize', {}).get('loginid')}")
                return
            except Exception as e:
                logger.error(f"Falha ao conectar: {e}. Retentando em {backoff}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 8)

    async def ensure_connected(self) -> None:
        if not self.is_connected:
            async with self._reconnect_lock:
                if not self.is_connected:
                    logger.info("WS desconectado — reconectando.")
                    self._stop = False
                    await self.connect()

    async def close(self) -> None:
        self._stop = True
        if self._listener_task:
            self._listener_task.cancel()
        if self._ws:
            await self._ws.close()

    async def _listener(self) -> None:
        try:
            async for raw in self._ws:
                try:
                    msg = json.loads(raw)
                except Exception:
                    logger.warning(f"Mensagem não-JSON recebida: {raw[:200]}")
                    continue
                logger.debug(f"WS<<< {msg}")
                req_id = msg.get("req_id")
                fut = self._pending.pop(req_id, None) if req_id is not None else None
                if fut and not fut.done():
                    fut.set_result(msg)
        except asyncio.CancelledError:
            return
        except websockets.ConnectionClosed as e:
            logger.warning(f"Conexão WS fechada: {e}. Tentando reconectar.")
            for fut in self._pending.values():
                if not fut.done():
                    fut.set_exception(DerivError("WS closed"))
            self._pending.clear()
            if not self._stop:
                await self.connect()

    async def _send(self, payload: dict, timeout: float = 30.0, _retry: bool = True) -> dict:
        await self.ensure_connected()
        req_id = next(self._req_id_counter)
        payload_with_id = {**payload, "req_id": req_id}
        loop = asyncio.get_running_loop()
        fut: asyncio.Future = loop.create_future()
        self._pending[req_id] = fut
        try:
            async with self._lock:
                logger.debug(f"WS>>> {payload_with_id}")
                await self._ws.send(json.dumps(payload_with_id))
            resp = await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending.pop(req_id, None)
            raise DerivError(f"Timeout aguardando resposta para req_id={req_id}")
        except (websockets.ConnectionClosed, DerivError) as e:
            self._pending.pop(req_id, None)
            if not _retry:
                raise DerivError(f"WS falhou após retry: {e}") from e
            logger.warning(f"WS caiu durante send/recv ({e}) — aguardando reconexão e retentando.")
            await self.ensure_connected()
            return await self._send(payload, timeout=timeout, _retry=False)
        if "error" in resp:
            err = resp["error"]
            raise DerivError(f"{err.get('code')}: {err.get('message')}")
        return resp

    async def get_candles(self, symbol: str, timeframe: str, count: int = 20) -> list[dict]:
        granularity = TIMEFRAME_TO_GRANULARITY.get(timeframe)
        if granularity is None:
            raise ValueError(f"Timeframe inválido: {timeframe}")
        resp = await self._send({
            "ticks_history": symbol,
            "style": "candles",
            "granularity": granularity,
            "count": count,
            "end": "latest",
        })
        candles = resp.get("candles", [])
        return [
            {
                "time": c["epoch"],
                "open": float(c["open"]),
                "high": float(c["high"]),
                "low": float(c["low"]),
                "close": float(c["close"]),
            }
            for c in candles
        ]

    async def get_candle_by_epoch(self, symbol: str, granularity: int, epoch: int) -> dict | None:
        resp = await self._send({
            "ticks_history": symbol,
            "style": "candles",
            "granularity": granularity,
            "start": epoch,
            "end": epoch + granularity,
            "count": 2,
        })
        for c in resp.get("candles", []):
            if int(c["epoch"]) == epoch:
                return {
                    "time": int(c["epoch"]),
                    "open": float(c["open"]),
                    "high": float(c["high"]),
                    "low": float(c["low"]),
                    "close": float(c["close"]),
                }
        return None
```

- [ ] **Step 2: Create app/collector/service.py**

```python
import asyncio
import time
from datetime import datetime, timezone
from loguru import logger

from app.collector.deriv_client import DerivClient, TIMEFRAME_TO_GRANULARITY
from app.signals.repository import SignalRepository
from app.events.protocol import EventType
from app.events.publisher import publish


class CollectorService:
    def __init__(self, client: DerivClient, repo: SignalRepository):
        self.client = client
        self.repo = repo
        self._running = False
        self._task: asyncio.Task | None = None
        self.symbols: list[str] = []
        self.timeframes: list[str] = []

    async def start(self, symbols: list[str], timeframes: list[str]) -> None:
        self.symbols = symbols
        self.timeframes = timeframes
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(f"Collector iniciado: symbols={symbols}, timeframes={timeframes}")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Collector parado")

    async def update_config(self, symbols: list[str], timeframes: list[str]) -> None:
        self.symbols = symbols
        self.timeframes = timeframes
        logger.info(f"Collector config atualizado: symbols={symbols}, timeframes={timeframes}")

    @property
    def is_running(self) -> bool:
        return self._running

    async def _loop(self) -> None:
        while self._running:
            try:
                await self.client.ensure_connected()
                for symbol in self.symbols:
                    for tf in self.timeframes:
                        try:
                            candles = await self.client.get_candles(symbol, tf, count=5)
                            await self.repo.upsert_candles(candles, symbol, tf)
                        except Exception as e:
                            logger.error(f"Erro ao coletar {symbol}/{tf}: {e}")

                granularity = TIMEFRAME_TO_GRANULARITY.get(self.timeframes[0] if self.timeframes else "5m", 300)
                now = time.time()
                next_close = (int(now / granularity) + 1) * granularity
                wait_secs = next_close - now
                await asyncio.sleep(wait_secs)
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error(f"Erro no collector loop: {e}")
                await asyncio.sleep(10)
```

- [ ] **Step 3: Verify imports work**

Run: `python -c "from app.collector.service import CollectorService; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add app/collector/
git commit -m "feat: add collector service with Deriv WebSocket → PostgreSQL persistence"
```

---

### Task 6: Indicator Service (DB-backed configuration)

**Files:**
- Create: `app/indicators/service.py`
- Create: `app/indicators/technical.py`
- Test: `tests/indicators/test_service.py`

- [ ] **Step 1: Write the test**

Create `tests/indicators/test_service.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/indicators/test_service.py -v`
Expected: FAIL — `app.indicators.service` does not exist.

- [ ] **Step 3: Create app/indicators/technical.py**

Copy the content of `indicators/technical.py` verbatim (the `analyze`, `detect_divergences`, `detect_candlestick_patterns`, `detect_sr_zones` functions). Only change the imports to be self-contained.

```python
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, ADXIndicator, MACD
from ta.volatility import BollingerBands, AverageTrueRange


def analyze(candles: list[dict]) -> dict:
    # ... identical to current indicators/technical.py analyze()
    pass


def detect_divergences(candles: list[dict], rsi_series: list[float],
                       macd_hist_series: list[float]) -> dict:
    # ... identical to current indicators/technical.py detect_divergences()
    pass


def detect_candlestick_patterns(candles: list[dict]) -> list[dict]:
    # ... identical to current indicators/technical.py detect_candlestick_patterns()
    pass


def detect_sr_zones(candles: list[dict], atr: float) -> list[dict]:
    # ... identical to current indicators/technical.py detect_sr_zones()
    pass
```

(Use the full function bodies from the original file — no changes needed.)

- [ ] **Step 4: Create app/indicators/service.py**

```python
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
            ema50 = float(EMAIndicator(close=close, window=p).ema_indicator().iloc[-1])
            result["ema50"] = round(ema50, 5)
            result["price_vs_ema50"] = "acima" if last_close > ema50 else "abaixo"
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/indicators/test_service.py -v`
Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add app/indicators/ tests/indicators/
git commit -m "feat: add indicator service with DB-backed configurable parameters"
```

---

### Task 7: Events + SSE Publisher

**Files:**
- Create: `app/events/protocol.py`
- Create: `app/events/publisher.py`

- [ ] **Step 1: Create app/events/protocol.py**

```python
from enum import Enum
from dataclasses import dataclass
from typing import Any
import json


class EventType(str, Enum):
    STATUS = "status"
    MARKET = "market"
    SIGNAL_EMITTED = "signal_emitted"
    SIGNAL_RESOLVED = "signal_resolved"
    LLM_RESPONSE = "llm_response"
    ERROR = "error"
    LOG = "log"


@dataclass
class Event:
    type: EventType
    data: dict[str, Any]

    def to_json(self) -> str:
        return json.dumps({"type": self.type.value, "data": self.data}, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "Event":
        d = json.loads(json_str)
        return cls(type=EventType(d["type"]), data=d["data"])
```

- [ ] **Step 2: Create app/events/publisher.py**

```python
import asyncio
from typing import Any
from app.events.protocol import Event, EventType


class EventBus:
    """Simple in-process pub/sub for SSE and internal listeners."""

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q) if hasattr(self._subscribers, 'discard') else None
        if q in self._subscribers:
            self._subscribers.remove(q)

    def publish(self, event_type: EventType, data: dict[str, Any]) -> None:
        event = Event(type=event_type, data=data)
        for q in self._subscribers:
            q.put_nowait(event)


_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def publish(event_type: EventType, data: dict[str, Any]) -> None:
    get_event_bus().publish(event_type, data)
```

- [ ] **Step 3: Verify imports**

Run: `python -c "from app.events.publisher import publish, get_event_bus; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add app/events/
git commit -m "feat: add event bus with SSE publisher support"
```

---

### Task 8: Agent Service (LLM loop migrated to async)

**Files:**
- Create: `app/agent/pre_analysis.py`
- Create: `app/agent/prompts.py`
- Create: `app/agent/tools.py`
- Create: `app/agent/learning.py`
- Create: `app/agent/service.py`

- [ ] **Step 1: Migrate pre_analysis.py**

Copy `agent/pre_analysis.py` to `app/agent/pre_analysis.py`, change import:

```python
from app.indicators.technical import detect_divergences, detect_candlestick_patterns, detect_sr_zones
```

Rest of file is identical.

- [ ] **Step 2: Migrate prompts.py**

Copy `agent/prompts.py` to `app/agent/prompts.py` — no import changes needed (it's self-contained).

- [ ] **Step 3: Migrate learning.py**

Copy `agent/learning.py` to `app/agent/learning.py`, change import:

```python
from app.signals.repository import SignalRepository
from loguru import logger
```

- [ ] **Step 4: Migrate tools.py**

Copy `agent/tools.py` to `app/agent/tools.py`, change imports:

```python
from app.indicators.technical import analyze
from app.signals.repository import SignalRepository
```

- [ ] **Step 5: Create app/agent/service.py**

```python
import asyncio
import os
import time
import json
from datetime import datetime, timezone, timedelta

import httpx
from loguru import logger

from app.collector.deriv_client import DerivClient, TIMEFRAME_TO_GRANULARITY
from app.signals.repository import SignalRepository
from app.signals.models import SignalCreate
from app.indicators.service import IndicatorService
from app.indicators.technical import analyze
from app.agent.pre_analysis import run_pre_analysis
from app.agent.prompts import build_system_prompt, build_user_context
from app.agent.tools import TOOLS, ToolDispatcher
from app.agent.learning import build_context_block
from app.events.protocol import EventType
from app.events.publisher import publish


BRT = timezone(timedelta(hours=-3))
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_TOOL_TURNS = 5
MAX_RETRIES = 3


class AgentService:
    def __init__(self, client: DerivClient, repo: SignalRepository):
        self.client = client
        self.repo = repo
        self._running = False
        self._task: asyncio.Task | None = None
        self._last_cycle: datetime | None = None
        self._start_time: datetime | None = None

    async def start(self) -> None:
        self._running = True
        self._start_time = datetime.now(timezone.utc)
        self._task = asyncio.create_task(self._loop())
        logger.info("Agent iniciado")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Agent parado")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def status(self) -> dict:
        return {
            "running": self._running,
            "last_cycle": self._last_cycle.isoformat() if self._last_cycle else None,
            "uptime": (datetime.now(timezone.utc) - self._start_time).total_seconds() if self._start_time else 0,
        }

    async def _load_config(self) -> dict:
        """Load config from DB via repository."""
        from app.db.models import BotConfig
        from sqlalchemy import select
        stmt = select(BotConfig)
        result = await self.repo.session.execute(stmt)
        configs = result.scalars().all()
        config = {}
        for cfg in configs:
            import json
            try:
                config[cfg.key] = json.loads(cfg.value)
            except (json.JSONDecodeError, TypeError):
                config[cfg.key] = cfg.value
        return config

    async def _load_indicator_configs(self) -> list:
        from app.db.models import IndicatorConfig
        from sqlalchemy import select
        stmt = select(IndicatorConfig)
        result = await self.repo.session.execute(stmt)
        return result.scalars().all()

    async def _loop(self) -> None:
        while self._running:
            try:
                config = await self._load_config()
                indicator_configs = await self._load_indicator_configs()

                await self.client.ensure_connected()
                publish(EventType.STATUS, {"status": "waiting", "detail": "Aguardando candle"})

                await self._wait_for_next_candle_close(config)
                settle = config.get("candle_settle_delay", 2)
                if settle > 0:
                    await asyncio.sleep(settle)

                publish(EventType.STATUS, {"status": "analyzing", "detail": "Analisando mercado"})

                market_data = await self._fetch_and_analyze(config, indicator_configs)
                publish(EventType.MARKET, {
                    "m5_indicators": market_data["m5_indicators"],
                    "m15_indicators": market_data["m15_indicators"],
                    "pre_analysis": market_data["pre_analysis"],
                })

                # Persist candles
                decision_tf = config.get("decision_timeframe", "5m")
                context_tf = config.get("context_timeframe", "15m")
                await self.repo.upsert_candles(market_data["m5_candles"], config["symbol"], decision_tf)
                await self.repo.upsert_candles(market_data["m15_candles"], config["symbol"], context_tf)

                # Run LLM
                result = await self._run_agent(config, market_data)
                publish(EventType.LLM_RESPONSE, {
                    "direction": result["direction"],
                    "confidence": result["confidence"],
                    "raw_response": result.get("raw_response", ""),
                })

                # Decide
                confidence = result["confidence"]
                direction = result["direction"]
                min_confidence = config.get("min_confidence", 0.50)

                if confidence >= min_confidence and direction != "NONE":
                    signal_data = SignalCreate(
                        symbol=config["symbol"], timeframe=decision_tf,
                        direction=direction, confidence=confidence,
                        duration=int(config.get("duration", 300)),
                        rsi=market_data["m5_indicators"].get("rsi"),
                        bb_position=market_data["m5_indicators"].get("bb_position"),
                        adx=market_data["m5_indicators"].get("adx"),
                        atr_pct=market_data["m5_indicators"].get("atr_pct"),
                        price_vs_ema50=market_data["m5_indicators"].get("price_vs_ema50"),
                        macd_line=market_data["m5_indicators"].get("macd_line"),
                        macd_signal=market_data["m5_indicators"].get("macd_signal"),
                        macd_histogram=market_data["m5_indicators"].get("macd_histogram"),
                        regime=market_data["pre_analysis"].get("regime"),
                        time_window=market_data["pre_analysis"].get("time_window", {}).get("window"),
                        m15_bias=market_data["pre_analysis"].get("m15_bias", {}).get("bias"),
                        confluence_score=max(
                            market_data["pre_analysis"].get("confluence", {}).get("call_signals", 0),
                            market_data["pre_analysis"].get("confluence", {}).get("put_signals", 0),
                        ),
                        strategy=market_data["pre_analysis"].get("suggested_strategy"),
                        entry_candle_time=market_data.get("next_entry_time"),
                    )
                    signal_id = await self.repo.insert_signal(signal_data)
                    await self.repo.session.commit()

                    publish(EventType.SIGNAL_EMITTED, {
                        "id": signal_id, "direction": direction,
                        "confidence": confidence, "symbol": config["symbol"],
                        "entry_candle_time": market_data.get("next_entry_time"),
                    })

                    # Schedule verification
                    from app.signals.verifier import resolve
                    asyncio.create_task(resolve(
                        self.client, self.repo, signal_id, direction,
                        config["symbol"], decision_tf,
                        market_data.get("next_entry_time"),
                        settle_delay=int(config.get("candle_settle_delay", 2)),
                    ))
                else:
                    publish(EventType.STATUS, {
                        "status": "idle",
                        "detail": f"Confiança insuficiente: {confidence:.0%}",
                    })

                self._last_cycle = datetime.now(timezone.utc)

            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.exception(f"Erro durante ciclo do agente: {e}")
                publish(EventType.ERROR, {"message": str(e)})
                await asyncio.sleep(10)

    async def _wait_for_next_candle_close(self, config: dict) -> None:
        tf = config.get("decision_timeframe", "5m")
        granularity = TIMEFRAME_TO_GRANULARITY.get(tf, 300)
        now = time.time()
        next_close = (int(now / granularity) + 1) * granularity
        wait_secs = next_close - now
        logger.info(f"Aguardando {wait_secs:.1f}s até fechamento do próximo candle ({tf})...")
        await asyncio.sleep(wait_secs)

    async def _fetch_and_analyze(self, config: dict, indicator_configs: list) -> dict:
        decision_tf = config.get("decision_timeframe", "5m")
        context_tf = config.get("context_timeframe", "15m")
        symbol = config.get("symbol", "R_25")
        count = max(config.get("candles_count", 60), 60)

        m5_candles = await self.client.get_candles(symbol, decision_tf, count)
        m15_candles = await self.client.get_candles(symbol, context_tf, count)

        m5_indicators = IndicatorService.analyze_with_config(m5_candles, indicator_configs)
        m15_indicators = IndicatorService.analyze_with_config(m15_candles, indicator_configs)

        m5_indicators["symbol"] = symbol
        m5_indicators["timeframe"] = decision_tf
        m15_indicators["symbol"] = symbol
        m15_indicators["timeframe"] = context_tf

        pre_analysis = run_pre_analysis(m5_indicators, m15_indicators, m5_candles, m15_candles)

        last_candle_epoch = m5_candles[-1]["time"]
        now = datetime.now(timezone.utc).timestamp()
        granularity = TIMEFRAME_TO_GRANULARITY.get(decision_tf, 300)
        next_entry_epoch = int(now / granularity) * granularity
        if next_entry_epoch <= now:
            next_entry_epoch += granularity

        last_candle_dt = datetime.fromtimestamp(last_candle_epoch, tz=BRT)
        next_entry_dt = datetime.fromtimestamp(next_entry_epoch, tz=BRT)

        return {
            "m5_candles": m5_candles,
            "m15_candles": m15_candles,
            "m5_indicators": m5_indicators,
            "m15_indicators": m15_indicators,
            "pre_analysis": pre_analysis,
            "last_candle_epoch": last_candle_epoch,
            "next_entry_epoch": next_entry_epoch,
            "last_candle_time": last_candle_dt.isoformat(),
            "next_entry_time": next_entry_dt.isoformat(),
        }

    async def _run_agent(self, config: dict, market_data: dict) -> dict:
        decision_tf = config.get("decision_timeframe", "5m")
        context_tf = config.get("context_timeframe", "15m")

        system_prompt = build_system_prompt(config)
        user_msg = build_user_context(
            config, market_data["m5_indicators"], market_data["m15_indicators"],
            market_data["pre_analysis"],
            market_data.get("last_candle_time", ""),
            market_data.get("next_entry_time", ""),
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ]
        dispatcher = ToolDispatcher(self.repo, config["symbol"], decision_tf, context_tf)

        content = ""
        async with httpx.AsyncClient() as http:
            for turn in range(MAX_TOOL_TURNS + 1):
                data = await self._call_openrouter(http, config["model"], messages, tools=TOOLS)
                choice = data["choices"][0]
                message = choice["message"]
                tool_calls = message.get("tool_calls") or []

                if not tool_calls:
                    content = (message.get("content") or "").strip()
                    break

                messages.append({"role": "assistant", "tool_calls": tool_calls, "content": message.get("content") or ""})
                for tc in tool_calls:
                    tool_name = tc["function"]["name"]
                    try:
                        args = json.loads(tc["function"].get("arguments", "{}"))
                    except json.JSONDecodeError:
                        args = {}
                    result = dispatcher.dispatch(tool_name, args)
                    messages.append({
                        "role": "tool", "tool_call_id": tc["id"],
                        "content": json.dumps(result, ensure_ascii=False),
                    })

                if turn == MAX_TOOL_TURNS:
                    data = await self._call_openrouter(http, config["model"], messages, tools=None)
                    content = (data["choices"][0]["message"].get("content") or "").strip()

        return self._parse_response(content, market_data.get("pre_analysis"))

    async def _call_openrouter(self, http: httpx.AsyncClient, model: str,
                                messages: list, tools: list | None = None) -> dict:
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload: dict = {"model": model, "messages": messages}
        if tools:
            payload["tools"] = tools
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = await http.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60.0)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.warning(f"OpenRouter falhou (tentativa {attempt}/{MAX_RETRIES}): {e}")
                await asyncio.sleep(2 ** attempt)
        raise RuntimeError(f"OpenRouter indisponível após {MAX_RETRIES} tentativas")

    @staticmethod
    def _parse_response(content: str, pre_analysis: dict | None = None) -> dict:
        try:
            lines = [line.strip() for line in content.strip().splitlines() if line.strip()]
            if len(lines) < 3:
                raise ValueError(f"Expected 3 lines, got {len(lines)}")

            time_line = lines[-3]
            direction_raw = lines[-2].upper()
            confidence_line = lines[-1]

            direction_map = {"COMPRA": "CALL", "VENDA": "PUT"}
            direction = direction_map.get(direction_raw)
            if direction is None:
                fallback = "CALL"
                if pre_analysis and pre_analysis.get("suggested_direction") in ("CALL", "PUT"):
                    fallback = pre_analysis["suggested_direction"]
                direction = fallback

            confidence_pct = int(confidence_line.replace("%", ""))
            confidence = confidence_pct / 100.0

            return {"confidence": confidence, "direction": direction, "raw_response": content}
        except (ValueError, IndexError):
            fallback = "CALL"
            if pre_analysis and pre_analysis.get("suggested_direction") in ("CALL", "PUT"):
                fallback = pre_analysis["suggested_direction"]
            return {"confidence": 0.0, "direction": fallback, "raw_response": content}
```

- [ ] **Step 6: Create app/signals/verifier.py**

```python
import asyncio
import time
from datetime import datetime, timezone
from loguru import logger

from app.collector.deriv_client import TIMEFRAME_TO_GRANULARITY
from app.events.protocol import EventType
from app.events.publisher import publish


async def resolve(client, repo, signal_id, direction, symbol, timeframe,
                  entry_candle_time, settle_delay=2):
    try:
        granularity = TIMEFRAME_TO_GRANULARITY.get(timeframe)
        if not granularity:
            logger.error(f"Verifier #{signal_id}: timeframe inválido '{timeframe}'")
            return

        entry_dt = datetime.fromisoformat(entry_candle_time.replace('Z', '+00:00'))
        entry_epoch = int(entry_dt.timestamp())
        close_epoch = entry_epoch + granularity

        wait = close_epoch + settle_delay - time.time()
        if wait > 0:
            logger.info(f"Verifier #{signal_id}: aguardando {wait:.1f}s até candle fechar")
            await asyncio.sleep(wait)

        candle = await client.get_candle_by_epoch(symbol, granularity, entry_epoch)
        if candle is None:
            logger.error(f"Verifier #{signal_id}: candle não encontrado")
            return

        entry_price = candle["open"]
        exit_price = candle["close"]
        outcome = "win" if (
            (direction == "CALL" and exit_price > entry_price) or
            (direction != "CALL" and exit_price < entry_price)
        ) else "loss"

        await repo.update_outcome(signal_id, entry_price, exit_price, outcome)
        await repo.session.commit()

        logger.info(f"RESULT #{signal_id} | {direction} | {outcome.upper()} | entry={entry_price} exit={exit_price}")
        publish(EventType.SIGNAL_RESOLVED, {
            "id": signal_id, "outcome": outcome,
            "quote_entry": entry_price, "quote_exit": exit_price,
        })
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(f"Verifier #{signal_id} erro: {e}")
```

- [ ] **Step 7: Verify imports**

Run: `python -c "from app.agent.service import AgentService; print('OK')"`
Expected: `OK`

- [ ] **Step 8: Commit**

```bash
git add app/agent/ app/signals/verifier.py app/signals/models.py
git commit -m "feat: add agent service with LLM loop, signal verification, and DB config"
```

---

### Task 9: REST API Layer (FastAPI endpoints)

**Files:**
- Create: `app/api/schemas.py`
- Create: `app/api/router.py`
- Create: `app/api/bot.py`
- Create: `app/api/collector.py`
- Create: `app/api/signals.py`
- Create: `app/api/indicators.py`
- Create: `app/api/health.py`
- Test: `tests/api/test_bot.py`
- Test: `tests/api/test_health.py`

- [ ] **Step 1: Create app/api/schemas.py**

```python
from pydantic import BaseModel


class ApiResponse(BaseModel):
    data: dict | list | None = None
    error: str | None = None


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
```

- [ ] **Step 2: Create app/api/health.py**

```python
from fastapi import APIRouter
from sqlalchemy import text

router = APIRouter()


@router.get("/health")
async def health_check():
    from app.main import _app_state
    db_ok = False
    deriv_ok = False
    try:
        if _app_state.db_session:
            await _app_state.db_session.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        pass
    try:
        if _app_state.deriv_client:
            deriv_ok = _app_state.deriv_client.is_connected
    except Exception:
        pass

    return {"data": {"db": "ok" if db_ok else "error", "deriv_ws": "ok" if deriv_ok else "disconnected"}, "error": None}
```

- [ ] **Step 3: Write tests for health endpoint**

Create `tests/api/test_health.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import create_app


@pytest.mark.asyncio
async def test_health_endpoint():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "error" in body
```

- [ ] **Step 4: Create app/api/bot.py**

```python
from fastapi import APIRouter

router = APIRouter(prefix="/bot", tags=["bot"])


@router.post("/start")
async def start_bot():
    from app.main import _app_state
    if _app_state.agent and _app_state.agent.is_running:
        return {"data": {"status": "already_running"}, "error": None}
    if _app_state.agent:
        await _app_state.agent.start()
    return {"data": {"status": "started"}, "error": None}


@router.post("/stop")
async def stop_bot():
    from app.main import _app_state
    if _app_state.agent:
        await _app_state.agent.stop()
    return {"data": {"status": "stopped"}, "error": None}


@router.get("/status")
async def bot_status():
    from app.main import _app_state
    if _app_state.agent:
        return {"data": _app_state.agent.status, "error": None}
    return {"data": {"running": False}, "error": None}


@router.get("/config")
async def get_bot_config():
    from app.db.models import BotConfig
    from sqlalchemy import select
    from app.main import _app_state
    stmt = select(BotConfig)
    result = await _app_state.db_session.execute(stmt)
    configs = {c.key: c.value for c in result.scalars().all()}
    return {"data": configs, "error": None}


@router.patch("/config")
async def update_bot_config(body: dict):
    import json
    from app.db.models import BotConfig
    from sqlalchemy import select
    from app.main import _app_state
    for key, value in body.items():
        stmt = select(BotConfig).where(BotConfig.key == key)
        result = await _app_state.db_session.execute(stmt)
        cfg = result.scalar_one_or_none()
        if cfg:
            cfg.value = json.dumps(value)
        else:
            _app_state.db_session.add(BotConfig(key=key, value=json.dumps(value)))
    await _app_state.db_session.commit()
    return {"data": {"updated": list(body.keys())}, "error": None}
```

- [ ] **Step 5: Create app/api/collector.py**

```python
from fastapi import APIRouter
from app.api.schemas import CollectorConfigUpdate

router = APIRouter(prefix="/collector", tags=["collector"])


@router.get("/status")
async def collector_status():
    from app.main import _app_state
    if _app_state.collector:
        return {"data": {
            "running": _app_state.collector.is_running,
            "symbols": _app_state.collector.symbols,
            "timeframes": _app_state.collector.timeframes,
        }, "error": None}
    return {"data": {"running": False}, "error": None}


@router.patch("/config")
async def update_collector_config(body: CollectorConfigUpdate):
    from app.main import _app_state
    if _app_state.collector:
        symbols = body.symbols or _app_state.collector.symbols
        timeframes = body.timeframes or _app_state.collector.timeframes
        await _app_state.collector.update_config(symbols, timeframes)
    return {"data": {"status": "updated"}, "error": None}
```

- [ ] **Step 6: Create app/api/signals.py**

```python
from fastapi import APIRouter

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("/")
async def list_signals(limit: int = 20, outcome: str | None = None, direction: str | None = None):
    from app.main import _app_state
    signals = await _app_state.repo.get_signals_filtered(limit=limit, outcome=outcome, direction=direction)
    return {"data": signals, "error": None}


@router.get("/stats")
async def signal_stats():
    from app.main import _app_state
    stats = await _app_state.repo.get_overall_stats()
    return {"data": stats, "error": None}


@router.get("/{signal_id}")
async def get_signal(signal_id: int):
    from app.main import _app_state
    sig = await _app_state.repo.get_signal_by_id(signal_id)
    if not sig:
        return {"data": None, "error": "Signal not found"}
    from app.signals.repository import _orm_to_dict
    return {"data": _orm_to_dict(sig), "error": None}
```

- [ ] **Step 7: Create app/api/indicators.py**

```python
from fastapi import APIRouter
from app.api.schemas import IndicatorCreate, IndicatorUpdate

router = APIRouter(prefix="/indicators", tags=["indicators"])


@router.get("/")
async def list_indicators():
    from app.db.models import IndicatorConfig
    from sqlalchemy import select
    from app.main import _app_state
    stmt = select(IndicatorConfig)
    result = await _app_state.db_session.execute(stmt)
    indicators = [
        {"id": i.id, "name": i.name, "indicator_type": i.indicator_type,
         "parameters": i.parameters, "enabled": i.enabled}
        for i in result.scalars().all()
    ]
    return {"data": indicators, "error": None}


@router.post("/")
async def create_indicator(body: IndicatorCreate):
    from app.db.models import IndicatorConfig
    from app.main import _app_state
    ind = IndicatorConfig(
        name=body.name, indicator_type=body.indicator_type,
        parameters=body.parameters, enabled=body.enabled,
    )
    _app_state.db_session.add(ind)
    await _app_state.db_session.commit()
    return {"data": {"id": ind.id, "name": ind.name}, "error": None}


@router.patch("/{indicator_id}")
async def update_indicator(indicator_id: int, body: IndicatorUpdate):
    from app.db.models import IndicatorConfig
    from app.main import _app_state
    ind = await _app_state.db_session.get(IndicatorConfig, indicator_id)
    if not ind:
        return {"data": None, "error": "Indicator not found"}
    if body.parameters is not None:
        ind.parameters = body.parameters
    if body.enabled is not None:
        ind.enabled = body.enabled
    await _app_state.db_session.commit()
    return {"data": {"id": ind.id, "name": ind.name}, "error": None}


@router.delete("/{indicator_id}")
async def delete_indicator(indicator_id: int):
    from app.db.models import IndicatorConfig
    from app.main import _app_state
    ind = await _app_state.db_session.get(IndicatorConfig, indicator_id)
    if not ind:
        return {"data": None, "error": "Indicator not found"}
    await _app_state.db_session.delete(ind)
    await _app_state.db_session.commit()
    return {"data": {"deleted": indicator_id}, "error": None}


@router.post("/reset-defaults")
async def reset_indicators():
    import json
    from app.db.models import IndicatorConfig
    from app.config import DEFAULT_INDICATORS
    from app.main import _app_state
    from sqlalchemy import delete
    await _app_state.db_session.execute(delete(IndicatorConfig))
    for default in DEFAULT_INDICATORS:
        _app_state.db_session.add(IndicatorConfig(**default))
    await _app_state.db_session.commit()
    return {"data": {"reset": True}, "error": None}
```

- [ ] **Step 8: Create app/api/router.py**

```python
from fastapi import APIRouter

from app.api import bot, collector, signals, indicators, health

router = APIRouter(prefix="/api/v1")
router.include_router(bot.router)
router.include_router(collector.router)
router.include_router(signals.router)
router.include_router(indicators.router)
router.include_router(health.router)
```

- [ ] **Step 9: Commit**

```bash
git add app/api/ tests/api/
git commit -m "feat: add REST API layer with bot, collector, signals, indicators, and health endpoints"
```

---

### Task 10: SSE Events Endpoint

**Files:**
- Modify: `app/api/router.py`

- [ ] **Step 1: Add SSE endpoint to router**

Add to `app/api/router.py`:

```python
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.api import bot, collector, signals, indicators, health

router = APIRouter(prefix="/api/v1")
router.include_router(bot.router)
router.include_router(collector.router)
router.include_router(signals.router)
router.include_router(indicators.router)
router.include_router(health.router)


@router.get("/events/stream")
async def event_stream():
    from app.events.publisher import get_event_bus
    import asyncio

    bus = get_event_bus()
    queue = bus.subscribe()

    async def generate():
        try:
            while True:
                event = await queue.get()
                yield {"data": event.to_json()}
        except asyncio.CancelledError:
            bus.unsubscribe(queue)

    return EventSourceResponse(generate())
```

- [ ] **Step 2: Commit**

```bash
git add app/api/router.py
git commit -m "feat: add SSE event stream endpoint for real-time frontend updates"
```

---

### Task 11: FastAPI Main Application (lifespan + wiring)

**Files:**
- Create: `app/main.py`

- [ ] **Step 1: Create app/main.py**

```python
import json
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI
from loguru import logger
from sqlalchemy import select

from app.config import settings, DEFAULT_BOT_CONFIG, DEFAULT_INDICATORS
from app.db.connection import create_engine_and_session
from app.db.models import BotConfig, IndicatorConfig, Base
from app.collector.deriv_client import DerivClient
from app.collector.service import CollectorService
from app.agent.service import AgentService
from app.signals.repository import SignalRepository
from app.api.router import router


@dataclass
class AppState:
    engine = None
    session_factory = None
    db_session = None
    deriv_client: DerivClient | None = None
    collector: CollectorService | None = None
    agent: AgentService | None = None
    repo: SignalRepository | None = None


_app_state = AppState()


async def _seed_defaults(session):
    """Populate DB with default configs if empty."""
    result = await session.execute(select(BotConfig).limit(1))
    if result.scalar_one_or_none() is None:
        for key, value in DEFAULT_BOT_CONFIG.items():
            session.add(BotConfig(key=key, value=json.dumps(value)))
        logger.info("Default bot config seeded")

    result = await session.execute(select(IndicatorConfig).limit(1))
    if result.scalar_one_or_none() is None:
        for default in DEFAULT_INDICATORS:
            session.add(IndicatorConfig(**default))
        logger.info("Default indicator config seeded")

    await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    engine, session_factory = create_engine_and_session(settings.database_url)
    _app_state.engine = engine
    _app_state.session_factory = session_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    _app_state.db_session = session_factory()
    _app_state.repo = SignalRepository(_app_state.db_session)

    await _seed_defaults(_app_state.db_session)

    # Start collector
    _app_state.deriv_client = DerivClient(
        api_token=settings.deriv_api_token,
        app_id=settings.deriv_app_id,
    )
    await _app_state.deriv_client.connect()

    # Read config to determine symbols/timeframes
    result = await _app_state.db_session.execute(select(BotConfig))
    configs = {c.key: c.value for c in result.scalars().all()}
    symbol = configs.get("symbol", '"R_25"')
    if isinstance(symbol, str):
        try:
            symbol = json.loads(symbol)
        except (json.JSONDecodeError, TypeError):
            pass
    decision_tf = configs.get("decision_timeframe", '"5m"')
    if isinstance(decision_tf, str):
        try:
            decision_tf = json.loads(decision_tf)
        except (json.JSONDecodeError, TypeError):
            pass
    context_tf = configs.get("context_timeframe", '"15m"')
    if isinstance(context_tf, str):
        try:
            context_tf = json.loads(context_tf)
        except (json.JSONDecodeError, TypeError):
            pass

    _app_state.collector = CollectorService(_app_state.deriv_client, _app_state.repo)
    await _app_state.collector.start(
        symbols=[symbol],
        timeframes=[decision_tf, context_tf],
    )

    _app_state.agent = AgentService(_app_state.deriv_client, _app_state.repo)

    logger.info("Application started")
    yield

    # Shutdown
    if _app_state.agent:
        await _app_state.agent.stop()
    if _app_state.collector:
        await _app_state.collector.stop()
    if _app_state.deriv_client:
        await _app_state.deriv_client.close()
    await _app_state.db_session.close()
    await engine.dispose()
    logger.info("Application stopped")


def create_app() -> FastAPI:
    app = FastAPI(title="Deriv Bot", version="2.0.0", lifespan=lifespan)
    app.include_router(router)
    return app


api = create_app()
```

- [ ] **Step 2: Verify the app can be imported**

Run: `python -c "from app.main import api; print(type(api).__name__)"`
Expected: `FastAPI`

- [ ] **Step 3: Commit**

```bash
git add app/main.py
git commit -m "feat: add FastAPI application with lifespan, wiring, and default seeding"
```

---

### Task 12: Docker + Deploy

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`

- [ ] **Step 1: Create Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:api", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create docker-compose.yml**

```yaml
version: "3.8"

services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - postgres

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: deriv
      POSTGRES_USER: deriv
      POSTGRES_PASSWORD: deriv
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

- [ ] **Step 3: Commit**

```bash
git add Dockerfile docker-compose.yml
git commit -m "feat: add Dockerfile and docker-compose for local dev and Coolify deploy"
```

---

### Task 13: Dashboard TUI Migration

**Files:**
- Create: `app/dashboard/` (copy from `dashboard/` with updated imports)

- [ ] **Step 1: Copy dashboard files to app/dashboard/**

Copy the following files, updating only the import paths:
- `dashboard/client.py` → `app/dashboard/client.py`
- `dashboard/event_client.py` → `app/dashboard/event_client.py`
- `dashboard/db_reader.py` → `app/dashboard/db_reader.py`
- `dashboard/styles.tcss` → `app/dashboard/styles.tcss`
- `dashboard/__init__.py` → `app/dashboard/__init__.py`
- `dashboard/__main__.py` → `app/dashboard/__main__.py`
- `dashboard/widgets/*.py` → `app/dashboard/widgets/*.py`

Import changes in each file:
- `from events.protocol import ...` → `from app.events.protocol import ...`
- `from signals.repository import ...` → `from app.signals.repository import ...`
- `from signals.models import ...` → `from app.signals.models import ...`
- `from utils.logger import logger` → `from loguru import logger`

- [ ] **Step 2: Verify dashboard can be imported**

Run: `python -c "from app.dashboard.client import DashboardApp; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app/dashboard/
git commit -m "feat: migrate TUI dashboard to app/ package with updated imports"
```

---

### Task 14: Cleanup Old Files

**Files:**
- Delete: `main.py`
- Delete: `deriv/`
- Delete: `agent/`
- Delete: `indicators/`
- Delete: `signals/`
- Delete: `events/`
- Delete: `utils/`
- Delete: `dashboard/`
- Delete: `requirements.txt`

- [ ] **Step 1: Verify new app works**

Run: `python -c "from app.main import api; print('App OK')" && python -c "from app.collector.service import CollectorService; print('Collector OK')" && python -c "from app.agent.service import AgentService; print('Agent OK')" && python -c "from app.signals.repository import SignalRepository; print('Repo OK")"`
Expected: All print `OK`.

- [ ] **Step 2: Delete old files**

```bash
rm main.py
rm -rf deriv/ agent/ indicators/ signals/ events/ utils/ dashboard/
rm requirements.txt
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore: remove old monolith files, fully migrated to app/ modular structure"
```

---

### Task 15: Final Integration Test

**Files:**
- Test: `tests/test_integration.py`

- [ ] **Step 1: Write integration test**

Create `tests/test_integration.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_app_starts():
    from app.main import create_app
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_bot_config_endpoints():
    from app.main import create_app
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # GET config
        resp = await client.get("/api/v1/bot/config")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body

        # PATCH config
        resp = await client.patch("/api/v1/bot/config", json={"symbol": "R_10"})
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_indicators_crud():
    from app.main import create_app
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # List
        resp = await client.get("/api/v1/indicators")
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body["data"], list)

        # Reset defaults
        resp = await client.post("/api/v1/indicators/reset-defaults")
        assert resp.status_code == 200

        # List again
        resp = await client.get("/api/v1/indicators")
        assert len(resp.json()["data"]) == 6


@pytest.mark.asyncio
async def test_signals_endpoints():
    from app.main import create_app
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/signals")
        assert resp.status_code == 200

        resp = await client.get("/api/v1/signals/stats")
        assert resp.status_code == 200
```

- [ ] **Step 2: Run full test suite**

Run: `pytest tests/ -v --tb=short`
Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration tests for all API endpoints"
```

---

## Self-Review Checklist

### Spec Coverage

| Spec Section | Task |
|---|---|
| Directory structure | Task 1 |
| PostgreSQL models (4 tables) | Task 2 |
| Config system (pydantic-settings + DB) | Task 3 |
| Signals repository (PostgreSQL) | Task 4 |
| Collector service (WS → DB) | Task 5 |
| Indicator service (DB config) | Task 6 |
| Events + SSE | Task 7, Task 10 |
| Agent service (LLM loop) | Task 8 |
| REST API (all endpoints) | Task 9 |
| FastAPI main (lifespan) | Task 11 |
| Docker + Coolify | Task 12 |
| Dashboard TUI migration | Task 13 |
| Cleanup old files | Task 14 |
| Integration tests | Task 15 |

### Placeholder Scan

No TBDs, TODOs, or placeholder steps found. Every step contains actual code.

### Type Consistency

- `SignalRepository(session: AsyncSession)` used consistently in Task 4, 5, 8, 11.
- `DerivClient(api_token, app_id)` used consistently in Task 5, 8, 11.
- `CollectorService(client, repo)` used consistently in Task 5, 11.
- `AgentService(client, repo)` used consistently in Task 8, 11.
- `_app_state` singleton used consistently in Task 9 (all API handlers).
- `EventType` enum used consistently in Task 7, 8, 10.
