import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
async def client():
    """Create a test client with mocked _app_state."""
    from app.api.router import router
    from fastapi import FastAPI
    import app.main as main_module

    app = FastAPI()
    app.include_router(router)

    mock_state = MagicMock()

    mock_state.agent = MagicMock()
    mock_state.agent.is_running = False
    mock_state.agent.status = {"running": False}
    mock_state.agent.start = AsyncMock()
    mock_state.agent.stop = AsyncMock()

    mock_state.collector = MagicMock()
    mock_state.collector.is_running = False
    mock_state.collector.symbols = []
    mock_state.collector.timeframes = []

    mock_state.deriv_client = MagicMock()
    mock_state.deriv_client.is_connected = False

    mock_state.repo = MagicMock()
    mock_state.repo.get_signals_filtered = AsyncMock(return_value=[])
    mock_state.repo.get_overall_stats = AsyncMock(return_value={
        "total": 0, "wins": 0, "losses": 0, "win_rate": 0.0, "avg_confidence": 0.0
    })

    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    mock_state.db_session = MagicMock()
    mock_state.db_session.execute = AsyncMock(return_value=execute_result)

    main_module._app_state = mock_state

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as c:
        yield c

    main_module._app_state = main_module.AppState()


@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert "data" in resp.json()


@pytest.mark.asyncio
async def test_bot_status(client):
    resp = await client.get("/api/v1/bot/status")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_bot_start(client):
    resp = await client.post("/api/v1/bot/start")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_bot_stop(client):
    resp = await client.post("/api/v1/bot/stop")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_collector_status(client):
    resp = await client.get("/api/v1/collector/status")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_signals_list(client):
    resp = await client.get("/api/v1/signals")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_signals_stats(client):
    resp = await client.get("/api/v1/signals/stats")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_indicators_list(client):
    resp = await client.get("/api/v1/indicators")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_events_stream(client):
    resp = await client.get("/api/v1/events/stream")
    assert resp.status_code == 200
