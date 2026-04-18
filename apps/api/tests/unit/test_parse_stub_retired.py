"""Regression tests for retired parse batch stubs (PR22-A)."""


import pytest


@pytest.mark.asyncio
async def test_parse_batch_endpoint_removed(client):
    response = await client.post("/parse/pdf/batch")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_parse_status_endpoint_removed(client):
    response = await client.get("/parse/pdf/status/fake-task-id")
    assert response.status_code == 404
