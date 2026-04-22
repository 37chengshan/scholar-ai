from app.models.retrieval import RetrievedChunk


def test_retrieved_chunk_accepts_evidence_bundle_fields():
    chunk = RetrievedChunk(
        paper_id="paper-1",
        text="Method A reaches 96.2 on CIFAR-10.",
        score=0.9,
        content_type="table",
        paper_role="result",
        table_ref="table-2",
        figure_ref=None,
        metric_sentence="Method A reaches 96.2 on CIFAR-10.",
        dataset="CIFAR-10",
        baseline="ResNet",
        method="Method A",
        score_value=96.2,
        metric_name="accuracy",
        metric_direction="higher_better",
        caption_text="Comparison of methods",
        evidence_bundle_id="bundle-1",
        evidence_types=["text", "table"],
    )

    dumped = chunk.model_dump()
    assert dumped["paper_role"] == "result"
    assert dumped["table_ref"] == "table-2"
    assert dumped["metric_name"] == "accuracy"
    assert dumped["evidence_bundle_id"] == "bundle-1"
    assert dumped["evidence_types"] == ["text", "table"]
