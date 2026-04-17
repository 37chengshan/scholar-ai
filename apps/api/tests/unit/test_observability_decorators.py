import pytest

from app.core.observability.decorators import observe_phase, observe_pipeline, observe_tool


@observe_phase("retrieving")
async def _phase_success():
    return "ok"


@observe_tool("rag_search")
async def _tool_success():
    return {"hits": 1}


@observe_pipeline("rag_query")
async def _pipeline_failure():
    raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_observe_phase_success_returns_original_result():
    result = await _phase_success()
    assert result == "ok"


@pytest.mark.asyncio
async def test_observe_tool_success_returns_original_result():
    result = await _tool_success()
    assert result["hits"] == 1


@pytest.mark.asyncio
async def test_observe_pipeline_failure_reraises_exception():
    with pytest.raises(RuntimeError, match="boom"):
        await _pipeline_failure()
