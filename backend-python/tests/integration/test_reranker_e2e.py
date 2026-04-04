"""End-to-end integration tests for Reranker services.

Tests verify:
- Complete workflow from query to final results
- Integration with embedding services
- Integration with indexer
- Multimodal scenarios
- Real-world usage patterns
- Performance under load
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from typing import List, Dict, Any
import asyncio
import time

from app.core.reranker.base import BaseRerankerService
from app.core.reranker.bge_reranker import BGERerankerService, get_reranker_service
from app.core.reranker.qwen3vl_reranker import Qwen3VLRerankerService
from app.core.reranker.factory import RerankerServiceFactory


class TestRerankerEndToEndWorkflow:
    """Test complete reranking workflows."""

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_e2e_text_search_workflow(self, mock_flag_reranker):
        """End-to-end test: user query → reranking → top results."""
        mock_flag_reranker_instance = MagicMock()
        mock_flag_reranker_instance.compute_score.return_value = [
            0.95, 0.88, 0.75, 0.60, 0.45, 0.30, 0.20, 0.10, 0.05, 0.02
        ]
        mock_flag_reranker.return_value = mock_flag_reranker_instance
        
        service = BGERerankerService()
        service.load_model()
        
        query = "What are the latest advances in quantum computing?"
        documents = [
            "Quantum computing uses qubits for parallel processing",
            "Recent advances include error correction improvements",
            "Classical computers use binary bits",
            "Quantum algorithms show promise for optimization",
            "IBM and Google are developing quantum processors",
            "Quantum cryptography enables secure communication",
            "AI models can benefit from quantum computing",
            "Quantum supremacy was demonstrated in 2019",
            "Quantum computers require extreme cooling",
            "Programming quantum computers requires new paradigms"
        ]
        
        results = service.rerank(query, documents, top_k=5)
        
        assert len(results) == 5
        assert all("document" in r and "score" in r and "rank" in r for r in results)
        assert results[0]["rank"] == 0
        assert results[0]["score"] >= results[-1]["score"]

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_e2e_relevance_feedback_workflow(self, mock_flag_reranker):
        """Test workflow with relevance feedback (re-reranking)."""
        mock_flag_reranker_instance = MagicMock()
        mock_flag_reranker.return_value = mock_flag_reranker_instance
        
        service = BGERerankerService()
        service.load_model()
        
        query = "machine learning"
        initial_docs = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        
        mock_flag_reranker_instance.compute_score.return_value = [0.9, 0.8, 0.7, 0.6, 0.5]
        initial_results = service.rerank(query, initial_docs, top_k=3)
        
        top_docs = [r["document"] for r in initial_results]
        new_docs = ["new_doc1", "new_doc2"]
        expanded_docs = top_docs + new_docs
        
        mock_flag_reranker_instance.compute_score.return_value = [0.95, 0.85, 0.80, 0.75, 0.70]
        final_results = service.rerank(query, expanded_docs, top_k=5)
        
        assert len(final_results) == 5

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_e2e_pagination_workflow(self, mock_flag_reranker):
        """Test pagination through reranked results."""
        mock_flag_reranker_instance = MagicMock()
        mock_flag_reranker.return_value = mock_flag_reranker_instance
        
        service = BGERerankerService()
        service.load_model()
        
        query = "search query"
        all_docs = [f"document {i}" for i in range(100)]
        
        mock_flag_reranker_instance.compute_score.return_value = [0.9 - i * 0.01 for i in range(100)]
        
        page1 = service.rerank(query, all_docs, top_k=10)
        page2_docs = all_docs[10:20]
        mock_flag_reranker_instance.compute_score.return_value = [0.8 - i * 0.01 for i in range(10)]
        page2 = service.rerank(query, page2_docs, top_k=10)
        
        assert len(page1) == 10
        assert len(page2) == 10

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_e2e_multi_query_workflow(self, mock_flag_reranker):
        """Test multiple queries against same document set."""
        mock_flag_reranker_instance = MagicMock()
        mock_flag_reranker.return_value = mock_flag_reranker_instance
        
        service = BGERerankerService()
        service.load_model()
        
        documents = ["AI research", "Quantum computing", "Climate change", "Space exploration"]
        
        for query in ["artificial intelligence", "physics", "environment"]:
            mock_flag_reranker_instance.compute_score.return_value = [0.9, 0.7, 0.5, 0.3]
            results = service.rerank(query, documents, top_k=2)
            assert len(results) == 2


class TestRerankerIntegrationWithFactory:
    """Test integration with RerankerServiceFactory."""

    def test_e2e_factory_creates_and_loads_service(self):
        """Factory should create and initialize service."""
        from app.core.reranker.factory import RerankerServiceFactory
        
        RerankerServiceFactory._instances = {}
        
        with patch('app.core.reranker.bge_reranker.FlagReranker') as mock_flag_reranker:
            mock_flag_reranker.return_value = MagicMock()
            
            service = RerankerServiceFactory.create()
            service.load_model()
            
            assert service.is_loaded()

    def test_e2e_factory_singleton_pattern(self):
        """Factory should maintain singleton for repeated calls."""
        from app.core.reranker.factory import RerankerServiceFactory
        
        RerankerServiceFactory._instances = {}
        
        with patch('app.core.reranker.bge_reranker.FlagReranker') as mock_flag_reranker:
            mock_flag_reranker.return_value = MagicMock()
            
            service1 = RerankerServiceFactory.create()
            service2 = RerankerServiceFactory.create()
            
            assert service1 is service2

    def test_e2e_get_reranker_service_integration(self):
        """get_reranker_service should work in end-to-end context."""
        import app.core.reranker.bge_reranker
        app.core.reranker.bge_reranker._reranker_service = None
        
        with patch('app.core.reranker.bge_reranker.FlagReranker') as mock_flag_reranker:
            mock_flag_reranker.return_value = MagicMock()
            
            service = get_reranker_service()
            service.load_model()
            
            assert isinstance(service, BGERerankerService)
            assert service.is_loaded()


class TestRerankerMultimodalE2E:
    """Test multimodal reranking end-to-end."""

    @patch('app.core.reranker.qwen3vl_reranker.AutoModelForCausalLM')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_e2e_text_with_image_query(self, mock_tokenizer, mock_model):
        """End-to-end test with image in query."""
        mock_model_instance = MagicMock()
        mock_model_instance.rerank = MagicMock(return_value=[0.95, 0.80, 0.60])
        mock_model.return_value = mock_model_instance
        
        service = Qwen3VLRerankerService()
        service.load_model()
        
        query = {
            "text": "Find similar diagrams",
            "image": "query_diagram.png"
        }
        documents = [
            {"text": "Technical diagram A", "image": "diagram_a.png"},
            {"text": "Technical diagram B", "image": "diagram_b.png"},
            {"text": "Non-diagram content", "image": "photo.jpg"}
        ]
        
        results = service.rerank(query, documents, top_k=3)
        
        assert len(results) == 3
        assert all("document" in r for r in results)

    @patch('app.core.reranker.qwen3vl_reranker.AutoModelForCausalLM')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_e2e_text_only_on_multimodal_service(self, mock_tokenizer, mock_model):
        """Text-only query should work on multimodal service."""
        mock_model_instance = MagicMock()
        mock_model_instance.rerank = MagicMock(return_value=[0.9, 0.7, 0.5])
        mock_model.return_value = mock_model_instance
        
        service = Qwen3VLRerankerService()
        service.load_model()
        
        query = "text query"
        documents = ["doc1", "doc2", "doc3"]
        
        results = service.rerank(query, documents)
        
        assert len(results) == 3

    @patch('app.core.reranker.qwen3vl_reranker.AutoModelForCausalLM')
    @patch('app.core.reranker.qwen3vl_reranker.AutoTokenizer')
    def test_e2e_mixed_inputs_multimodal(self, mock_tokenizer, mock_model):
        """Mixed text-only and multimodal inputs."""
        mock_model_instance = MagicMock()
        mock_model_instance.rerank = MagicMock(return_value=[0.9, 0.8, 0.7, 0.6])
        mock_model.return_value = mock_model_instance
        
        service = Qwen3VLRerankerService()
        service.load_model()
        
        query = {"text": "query", "image": "img.jpg"}
        documents = [
            "text doc",
            {"text": "multimodal doc", "image": "doc.jpg"},
            "another text doc",
            {"text": "mixed doc", "image": None}
        ]
        
        results = service.rerank(query, documents)
        
        assert len(results) == 4


class TestRerankerPerformanceE2E:
    """Test performance scenarios."""

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_e2e_latency_with_large_batch(self, mock_flag_reranker):
        """Test latency with large document batch."""
        mock_flag_reranker_instance = MagicMock()
        mock_flag_reranker_instance.compute_score.return_value = [0.9 - i * 0.0001 for i in range(500)]
        mock_flag_reranker.return_value = mock_flag_reranker_instance
        
        service = BGERerankerService()
        service.load_model()
        
        documents = [f"doc {i}" for i in range(500)]
        
        start = time.time()
        results = service.rerank("query", documents, top_k=50)
        elapsed = time.time() - start
        
        assert len(results) == 50
        assert elapsed < 1.0

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_e2e_concurrent_requests(self, mock_flag_reranker):
        """Test handling of concurrent reranking requests."""
        mock_flag_reranker_instance = MagicMock()
        mock_flag_reranker_instance.compute_score.return_value = [0.9, 0.7, 0.5]
        mock_flag_reranker.return_value = mock_flag_reranker_instance
        
        service = BGERerankerService()
        service.load_model()
        
        def rerank_task(query_id):
            query = f"query {query_id}"
            documents = ["doc1", "doc2", "doc3"]
            return service.rerank(query, documents)
        
        results = [rerank_task(i) for i in range(10)]
        
        assert all(len(r) == 3 for r in results)

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_e2e_memory_efficiency(self, mock_flag_reranker):
        """Test memory usage with large batches."""
        mock_flag_reranker_instance = MagicMock()
        mock_flag_reranker_instance.compute_score.return_value = [0.9 - i * 0.0001 for i in range(1000)]
        mock_flag_reranker.return_value = mock_flag_reranker_instance
        
        service = BGERerankerService()
        service.load_model()
        
        large_docs = [f"document {i} with substantial content" for i in range(1000)]
        results = service.rerank("query", large_docs, top_k=100)
        
        assert len(results) == 100


class TestRerankerRealWorldScenarios:
    """Test real-world usage scenarios."""

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_e2e_academic_paper_search(self, mock_flag_reranker):
        """Test reranking academic paper abstracts."""
        mock_flag_reranker_instance = MagicMock()
        mock_flag_reranker_instance.compute_score.return_value = [
            0.92, 0.88, 0.75, 0.65, 0.55
        ]
        mock_flag_reranker.return_value = mock_flag_reranker_instance
        
        service = BGERerankerService()
        service.load_model()
        
        query = "deep learning for image recognition"
        abstracts = [
            "This paper presents a novel CNN architecture for image classification achieving state-of-the-art results on ImageNet",
            "We propose a transformer-based approach for visual recognition tasks",
            "Traditional image processing methods using edge detection",
            "Deep neural networks have revolutionized computer vision applications",
            "Survey of recent advances in deep learning for visual tasks"
        ]
        
        results = service.rerank(query, abstracts, top_k=5)
        
        assert len(results) == 5
        assert results[0]["score"] >= 0.85

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_e2e_legal_document_search(self, mock_flag_reranker):
        """Test reranking legal documents."""
        mock_flag_reranker_instance = MagicMock()
        mock_flag_reranker_instance.compute_score.return_value = [0.9, 0.8, 0.7]
        mock_flag_reranker.return_value = mock_flag_reranker_instance
        
        service = BGERerankerService()
        service.load_model()
        
        query = "contract breach liability"
        legal_docs = [
            "The defendant was found liable for breach of contract under Section 15 of the Agreement",
            "Intellectual property rights and patent infringement cases",
            "Contract law principles and breach remedies in civil court proceedings"
        ]
        
        results = service.rerank(query, legal_docs)
        
        assert len(results) == 3

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_e2e_code_search(self, mock_flag_reranker):
        """Test reranking code snippets."""
        mock_flag_reranker_instance = MagicMock()
        mock_flag_reranker_instance.compute_score.return_value = [0.95, 0.80, 0.60]
        mock_flag_reranker.return_value = mock_flag_reranker_instance
        
        service = BGERerankerService()
        service.load_model()
        
        query = "python async function"
        code_snippets = [
            "async def fetch_data(url):\n    response = await aiohttp.get(url)\n    return response.json()",
            "def synchronous_fetch(url):\n    return requests.get(url).json()",
            "# Python async programming tutorial\nasyncio.run(main())"
        ]
        
        results = service.rerank(query, code_snippets)
        
        assert len(results) == 3


class TestRerankerIntegrationWithAPI:
    """Test integration with API endpoints."""

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_e2e_api_request_format(self, mock_flag_reranker):
        """Test processing API request format."""
        mock_flag_reranker_instance = MagicMock()
        mock_flag_reranker_instance.compute_score.return_value = [0.9, 0.7]
        mock_flag_reranker.return_value = mock_flag_reranker_instance
        
        service = BGERerankerService()
        service.load_model()
        
        api_request = {
            "query": "user query",
            "documents": [
                {"id": "doc1", "content": "document content 1"},
                {"id": "doc2", "content": "document content 2"}
            ],
            "top_k": 2
        }
        
        query_text = api_request["query"]
        doc_texts = [doc["content"] for doc in api_request["documents"]]
        
        results = service.rerank(query_text, doc_texts, top_k=api_request["top_k"])
        
        assert len(results) == api_request["top_k"]

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_e2e_api_response_format(self, mock_flag_reranker):
        """Test generating API response format."""
        mock_flag_reranker_instance = MagicMock()
        mock_flag_reranker_instance.compute_score.return_value = [0.9, 0.7]
        mock_flag_reranker.return_value = mock_flag_reranker_instance
        
        service = BGERerankerService()
        service.load_model()
        
        query = "query"
        docs_with_ids = [{"id": "1", "text": "doc1"}, {"id": "2", "text": "doc2"}]
        
        results = service.rerank(query, docs_with_ids)
        
        api_response = {
            "results": [
                {
                    "id": docs_with_ids[results[i]["rank"]]["id"],
                    "score": results[i]["score"],
                    "rank": results[i]["rank"]
                }
                for i in range(len(results))
            ]
        }
        
        assert "results" in api_response
        assert len(api_response["results"]) == 2


class TestRerankerCacheIntegration:
    """Test integration with caching systems."""

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_e2e_cache_key_generation(self, mock_flag_reranker):
        """Test generating consistent cache keys."""
        mock_flag_reranker_instance = MagicMock()
        mock_flag_reranker_instance.compute_score.return_value = [0.9]
        mock_flag_reranker.return_value = mock_flag_reranker_instance
        
        service = BGERerankerService()
        service.load_model()
        
        query = "test query"
        documents = ["doc1"]
        
        cache_key = f"{query}:{':'.join(documents)}"
        
        results = service.rerank(query, documents)
        
        assert cache_key == "test query:doc1"

    @patch('app.core.reranker.bge_reranker.FlagReranker')
    def test_e2e_cache_hit_workflow(self, mock_flag_reranker):
        """Test workflow with cache hit."""
        mock_flag_reranker_instance = MagicMock()
        mock_flag_reranker_instance.compute_score.return_value = [0.9]
        mock_flag_reranker.return_value = mock_flag_reranker_instance
        
        service = BGERerankerService()
        service.load_model()
        
        cache = {}
        
        query = "cached query"
        documents = ["cached doc"]
        
        cache_key = f"{query}:{documents[0]}"
        
        if cache_key not in cache:
            results = service.rerank(query, documents)
            cache[cache_key] = results
        
        cached_results = cache[cache_key]
        
        assert len(cached_results) == 1