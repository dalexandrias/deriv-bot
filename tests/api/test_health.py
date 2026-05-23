import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import _app_state, api


@pytest.fixture(autouse=True)
def _mock_app_state():
    """Mock _app_state so tests don't need a real DB or Deriv connection."""
    mock_state = MagicMock()
    mock_state.db_session = AsyncMock()
    mock_state.db_session.execute = AsyncMock(return_value=MagicMock(scalar=MagicMock(return_value=1)))
    mock_state.deriv_client = MagicMock()
    mock_state.deriv_client.is_connected = True
    mock_state.agent = None
    mock_state.collector = None
    mock_state.repo = None
    patcher = patch("app.main._app_state", mock_state)
    patcher2 = patch("app.api.health._app_state", mock_state, create=True)
    patcher.start()
    patcher2.start()
    yield mock_state
    patcher.stop()
    patcher2.stop()


@pytest.fixture
async def client():
    transport = ASGITransport(app=api)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_health_endpoint(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["db"] == "ok"
    assert body["data"]["deriv_ws"] == "ok"
    assert body["error"] is None


async def test_health_db_error(client, _mock_app_state):
    _mock_app_state.db_session.execute.side_effect = Exception("DB down")
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["db"] == "error"


async def test_health_deriv_disconnected(client, _mock_app_state):
    _mock_app_state.deriv_client.is_connected = False
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["deriv_ws"] == "disconnected"


async def test_health_no_deriv_client(client, _mock_app_state):
    _mock_app_state.deriv_client = None
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["deriv_ws"] == "disconnected"
