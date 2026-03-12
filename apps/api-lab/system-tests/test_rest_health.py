"""System tests for REST API health endpoints."""

import pytest


@pytest.mark.asyncio
async def test_healthz(rest_client):
    resp = await rest_client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_ready(rest_client):
    resp = await rest_client.get("/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_info(rest_client):
    resp = await rest_client.get("/info")
    assert resp.status_code == 200
    data = resp.json()
    assert "component" in data
    assert "environment" in data
    assert data["component"] == "python-rest-api"
