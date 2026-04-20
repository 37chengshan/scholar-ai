import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.docling_service import DoclingParser, ParserConfig


@pytest.mark.asyncio
async def test_parse_pdf_returns_fallback_result_when_docling_fails():
    parser = DoclingParser(config=ParserConfig())

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(b'%PDF-1.4 test')
        tmp_path = tmp.name

    fallback_result = {
        'markdown': 'fallback markdown',
        'items': [{'type': 'text', 'text': 'fallback text', 'page': 1, 'bbox': None}],
        'page_count': 1,
        'metadata': {
            'parse_mode': 'pypdf_fallback',
            'parse_warnings': ['docling_parse_failed_fallback_to_pypdf'],
        },
    }

    with patch.object(parser.native_converter, 'convert', side_effect=RuntimeError('snapshot download failed')):
        with patch.object(parser, '_parse_pdf_with_pypdf', new=AsyncMock(return_value=fallback_result)) as fallback_mock:
            result = await parser.parse_pdf(tmp_path)

    assert result['metadata']['parse_mode'] == 'pypdf_fallback'
    assert result['page_count'] == 1
    fallback_mock.assert_awaited_once()

    Path(tmp_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_parse_pdf_raises_original_error_when_fallback_unavailable():
    parser = DoclingParser(config=ParserConfig())

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(b'%PDF-1.4 test')
        tmp_path = tmp.name

    with patch.object(parser.native_converter, 'convert', side_effect=RuntimeError('primary failed')):
        with patch.object(parser, '_parse_pdf_with_pypdf', new=AsyncMock(return_value=None)):
            with pytest.raises(RuntimeError, match='primary failed'):
                await parser.parse_pdf(tmp_path)

    Path(tmp_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_pypdf_fallback_extracts_text_pages():
    parser = DoclingParser(config=ParserConfig())

    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(b'%PDF-1.4 test')
        tmp_path = tmp.name

    page_one = Mock()
    page_one.extract_text.return_value = 'First page text'
    page_two = Mock()
    page_two.extract_text.return_value = 'Second page text'

    reader_mock = Mock()
    reader_mock.pages = [page_one, page_two]

    with patch('pypdf.PdfReader', return_value=reader_mock):
        result = await parser._parse_pdf_with_pypdf(Path(tmp_path), RuntimeError('docling failed'))

    assert result is not None
    assert result['page_count'] == 2
    assert result['metadata']['parse_mode'] == 'pypdf_fallback'
    assert len(result['items']) == 2
    assert 'First page text' in result['markdown']

    Path(tmp_path).unlink(missing_ok=True)
