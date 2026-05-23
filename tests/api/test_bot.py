import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import api


def _make_mock_state():
    """Create a fresh mock of _app_state with sensible defaults."""
    mock_state = MagicMock()
    mock_state.db_session = AsyncMock()
    mock_state.deriv_client = MagicMock()
    mock_state.collector = MagicMock()
    mock_state.repo = MagicMock()

    # Agent mock
    mock_agent = MagicMock()
    mock_agent.is_running = False
    mock_agent.start = AsyncMock()
    mock_agent.stop = AsyncMock()
    mock_agent.status = {"running": False, "last_cycle": None, "uptime": 0}
    mock_state.agent = mock_agent

    # BotConfig query mock
    mock_config = MagicMock()
    mock_config.key = "symbol"
    mock_config.value = "R_25"
    mock_state.db_session.execute = AsyncMock(
        return_value=MagicMock(scalars=MagicMock(return_value=[mock_config]))
    )
    mock_state.db_session.get = AsyncMock(return_value=None)
    mock_state.db_session.add = MagicMock()
    mock_state.db_session.commit = AsyncMock()

    return mock_state


@pytest.fixture(autouse=True)
def _mock_app_state():
    mock_state = _make_mock_state()
    # Patch _app_state in all modules that import it lazily
    patchers = [
        patch("app.main._app_state", mock_state),
        patch("app.api.bot._app_state", mock_state, create=True),
    ]
    for p in patchers:
        p.start()
    yield mock_state
    for p in patchers:
        p.stop()


@pytest.fixture
async def client():
    transport = ASGITransport(app=api)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_bot_status_not_running(client):
    response = await client.get("/api/v1/bot/status")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["running"] is False
    assert body["error"] is None


async def test_bot_start(client, _mock_app_state):
    response = await client.post("/api/v1/bot/start")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "started"
    _mock_app_state.agent.start.assert_awaited_once()


async def test_bot_start_already_running(client, _mock_app_state):
    _mock_app_state.agent.is_running = True
    response = await client.post("/api/v1/bot/start")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "already_running"


async def test_bot_stop(client, _mock_app_state):
    _mock_app_state.agent.is_running = True
    response = await client.post("/api/v1/bot/stop")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "stopped"
    _mock_app_state.agent.stop.assert_awaited_once()


async def test_bot_config_get(client, _mock_app_state):
    cfg1 = MagicMock()
    cfg1.key = "symbol"
    cfg1.value = "R_25"
    cfg2 = MagicMock()
    cfg2.key = "decision_timeframe"
    cfg2.value = "5m"
    _mock_app_state.db_session.execute = AsyncMock(
        return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[cfg1, cfg2]))))
    )
    response = await client.get("/api/v1/bot/config")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["symbol"] == "R_25"
    assert body["data"]["decision_timeframe"] == "5m"


async def test_bot_config_update(client, _mock_app_state):
    # Mock select to return None (config doesn't exist yet)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)
    _mock_app_state.db_session.execute = AsyncMock(return_value=mock_result)

    response = await client.patch("/api/v1/bot/config", json={"symbol": "R_50"})
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["updated"] == ["symbol"]
    _mock_app_state.db_session.add.assert_called_once()
    _mock_app_state.db_session.commit.assert_awaited_once()
