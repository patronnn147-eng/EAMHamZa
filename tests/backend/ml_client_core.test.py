"""Unit tests for app/backend/core/ml_client.py (MLClient + module-level helpers)."""
from unittest.mock import AsyncMock, MagicMock

import pytest

import core.ml_client as ml_client_mod
from core.ml_client import (
    MLClient,
    get_ml_predictions,
    get_model_metrics,
    is_ml_service_available,
)


def _fake_response(json_data=None, status_code=200):
    resp = MagicMock()
    resp.json.return_value = json_data or {}
    resp.status_code = status_code
    return resp


# ── get_client / close ────────────────────────────────────────────────────────

def test_get_client_creates_and_caches_instance():
    client = MLClient(base_url="http://x")
    a = client.get_client()
    b = client.get_client()
    assert a is b


@pytest.mark.asyncio
async def test_close_clears_cached_client():
    client = MLClient(base_url="http://x")
    inner = client.get_client()
    inner.aclose = AsyncMock()
    await client.close()
    assert client._client is None
    inner.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_is_noop_when_no_client_created():
    client = MLClient(base_url="http://x")
    await client.close()  # must not raise
    assert client._client is None


# ── health_check ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_check_returns_parsed_json(monkeypatch):
    client = MLClient(base_url="http://x")
    fake_http = MagicMock()
    fake_http.get = AsyncMock(return_value=_fake_response({"status": "healthy"}))
    monkeypatch.setattr(client, "get_client", lambda: fake_http)

    result = await client.health_check()
    assert result == {"status": "healthy"}


@pytest.mark.asyncio
async def test_health_check_swallows_exception(monkeypatch):
    client = MLClient(base_url="http://x")
    fake_http = MagicMock()
    fake_http.get = AsyncMock(side_effect=RuntimeError("down"))
    monkeypatch.setattr(client, "get_client", lambda: fake_http)

    result = await client.health_check()
    assert result["status"] == "unhealthy"
    assert "down" in result["error"]


# ── is_ml_service_available ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_is_ml_service_available_true_when_healthy(monkeypatch):
    monkeypatch.setattr(
        ml_client_mod.ml_client, "health_check", AsyncMock(return_value={"status": "healthy"})
    )
    assert await is_ml_service_available() is True


@pytest.mark.asyncio
async def test_is_ml_service_available_false_when_unhealthy(monkeypatch):
    monkeypatch.setattr(
        ml_client_mod.ml_client, "health_check", AsyncMock(return_value={"status": "unhealthy"})
    )
    assert await is_ml_service_available() is False


@pytest.mark.asyncio
async def test_is_ml_service_available_false_on_exception(monkeypatch):
    monkeypatch.setattr(
        ml_client_mod.ml_client, "health_check", AsyncMock(side_effect=RuntimeError("boom"))
    )
    assert await is_ml_service_available() is False


# ── get_ml_predictions ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_ml_predictions_delegates_to_predict_all(monkeypatch):
    predict_mock = AsyncMock(return_value={"unified_health_score": 90.0})
    monkeypatch.setattr(ml_client_mod.ml_client, "predict_all", predict_mock)

    result = await get_ml_predictions(300.0, 310.0, 1500, 40.0, 10)
    assert result == {"unified_health_score": 90.0}
    predict_mock.assert_awaited_once_with(300.0, 310.0, 1500, 40.0, 10)


# ── get_model_metrics ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_model_metrics_success(monkeypatch):
    fake_http = MagicMock()
    fake_http.get = AsyncMock(return_value=_fake_response({"accuracy": 0.9}, status_code=200))
    monkeypatch.setattr(ml_client_mod.ml_client, "get_client", lambda: fake_http)

    result = await get_model_metrics()
    assert result == {"accuracy": 0.9}


@pytest.mark.asyncio
async def test_get_model_metrics_non_200_returns_error(monkeypatch):
    fake_http = MagicMock()
    fake_http.get = AsyncMock(return_value=_fake_response({}, status_code=500))
    monkeypatch.setattr(ml_client_mod.ml_client, "get_client", lambda: fake_http)

    result = await get_model_metrics()
    assert result["success"] is False


@pytest.mark.asyncio
async def test_get_model_metrics_swallows_exception(monkeypatch):
    fake_http = MagicMock()
    fake_http.get = AsyncMock(side_effect=RuntimeError("down"))
    monkeypatch.setattr(ml_client_mod.ml_client, "get_client", lambda: fake_http)

    result = await get_model_metrics()
    assert result["success"] is False
    assert "down" in result["error"]
