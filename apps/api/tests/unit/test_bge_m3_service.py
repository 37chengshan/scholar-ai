from unittest.mock import Mock

from app.core.bge_m3_service import BGEM3Service


def test_encode_text_normalizes_non_string_inputs() -> None:
    service = BGEM3Service()
    service._initialized = True

    model = Mock()
    model.encode.return_value = {
        "dense_vecs": Mock(
            tolist=lambda: [
                [0.1] * service.EMBEDDING_DIM,
                [0.2] * service.EMBEDDING_DIM,
                [0.3] * service.EMBEDDING_DIM,
                [0.4] * service.EMBEDDING_DIM,
                [0.5] * service.EMBEDDING_DIM,
            ]
        )
    }
    service.model = model

    result = service.encode_text([123, None, "ok", {"a": 1}, b"raw"])

    assert isinstance(result, list)
    assert len(result) == 5
    assert len(result[0]) == service.EMBEDDING_DIM
    assert result[1] == [0.0] * service.EMBEDDING_DIM
    model.encode.assert_called_once_with(
        ["123", "ok", '{"a": 1}', "raw"],
        batch_size=32,
        max_length=service.MAX_SEQ_LENGTH,
    )
