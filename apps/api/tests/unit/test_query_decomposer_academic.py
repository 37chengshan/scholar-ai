import pytest

from app.core.query_decomposer import QueryDecomposer


@pytest.mark.parametrize(
    "query,expected",
    [
        ("Compare method A and method B", "compare"),
        ("Show table 2 values", "table"),
        ("Show figure 3", "figure"),
        ("What is the accuracy score", "numeric"),
        ("What are the limitations", "limitation"),
        ("Critique this method", "critique"),
        ("How has this model evolved over versions", "evolution"),
    ],
)
def test_classify_query_extended_types(query, expected):
    decomposer = QueryDecomposer()
    assert decomposer.classify_query(query) == expected


@pytest.mark.asyncio
async def test_decompose_fact_query_returns_single_direct_item():
    decomposer = QueryDecomposer()

    result = await decomposer.decompose_query("What is the method?", "fact", ["paper-1"])
    assert result[0]["query_type"] == "fact"
    assert result[0]["question"] == "What is the method?"
