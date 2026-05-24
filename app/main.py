import json
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
    result = await session.execute(select(BotConfig).limit(1))
    if result.scalar_one_or_none() is None:
        for key, value in DEFAULT_BOT_CONFIG.items():
            session.add(BotConfig(key=key, value=value))
        logger.info("Default bot config seeded")
    result = await session.execute(select(IndicatorConfig).limit(1))
    if result.scalar_one_or_none() is None:
        for default in DEFAULT_INDICATORS:
            session.add(IndicatorConfig(**default))
        logger.info("Default indicator config seeded")
    await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine, session_factory = create_engine_and_session(settings.database_url)
    _app_state.engine = engine
    _app_state.session_factory = session_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    _app_state.db_session = session_factory()
    _app_state.repo = SignalRepository(_app_state.db_session)
    await _seed_defaults(_app_state.db_session)

    _app_state.deriv_client = DerivClient(
        api_token=settings.deriv_api_token,
        app_id=settings.deriv_app_id,
    )
    await _app_state.deriv_client.connect()

    result = await _app_state.db_session.execute(select(BotConfig))
    configs = {c.key: c.value for c in result.scalars().all()}
    symbol = configs.get("symbol", "R_25")
    if isinstance(symbol, str):
        try:
            symbol = json.loads(symbol)
        except Exception:
            pass
    decision_tf = configs.get("decision_timeframe", "5m")
    if isinstance(decision_tf, str):
        try:
            decision_tf = json.loads(decision_tf)
        except Exception:
            pass
    context_tf = configs.get("context_timeframe", "15m")
    if isinstance(context_tf, str):
        try:
            context_tf = json.loads(context_tf)
        except Exception:
            pass

    _app_state.collector = CollectorService(_app_state.deriv_client, _app_state.repo)
    await _app_state.collector.start(symbols=[symbol], timeframes=[decision_tf, context_tf])
    _app_state.agent = AgentService(_app_state.deriv_client, _app_state.session_factory)
    logger.info("Application started")
    yield

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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


api = create_app()
