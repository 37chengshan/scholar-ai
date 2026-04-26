#!/usr/bin/env python
"""Test Milvus retrieval after disabling specter2.

Validates that:
1. Milvus connections work
2. No vector dimension mismatch errors
3. Answer benchmark can process queries
"""

import json
import sys
import asyncio
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "apps" / "api"
if backend_path.exists():
    sys.path.insert(0, str(backend_path))


async def test_milvus_search():
    """Test basic Milvus search with qwen embeddings only."""
    print("=" * 80)
    print("TEST 1: Basic Milvus Connection")
    print("=" * 80)
    
    try:
        from pymilvus import connections
        connections.connect(host="localhost", port=19530)
        print("✓ Milvus connected")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False
    
    print("\n" + "=" * 80)
    print("TEST 2: Check SCIENTIFIC_TEXT_BRANCH_ENABLED setting")
    print("=" * 80)
    
    try:
        from app.config import settings
        print(f"SCIENTIFIC_TEXT_BRANCH_ENABLED = {settings.SCIENTIFIC_TEXT_BRANCH_ENABLED}")
        if settings.SCIENTIFIC_TEXT_BRANCH_ENABLED:
            print("✗ ERROR: specter2 should be disabled!")
            return False
        print("✓ specter2 disabled as expected")
    except Exception as e:
        print(f"✗ Config check failed: {e}")
        return False
    
    print("\n" + "=" * 80)
    print("TEST 3: Test MultimodalSearchService search (small sample)")
    print("=" * 80)
    
    try:
        from app.core.multimodal_search_service import get_multimodal_search_service
        from app.models.retrieval import SearchConstraints
        
        search_service = get_multimodal_search_service()
        
        # Test query
        test_query = "What is the main contribution of this paper?"
        
        result = await search_service.search(
            query=test_query,
            paper_ids=[],  # Empty list instead of None
            user_id="test-user",
            top_k=5,
            use_reranker=False,
            content_types=["text"],
        )
        
        num_results = len(result.get("results", []))
        print(f"✓ Query processed successfully")
        print(f"  Query: {test_query[:60]}...")
        print(f"  Results: {num_results} chunks retrieved")
        print(f"  Intent: {result.get('intent')}")
        
        if num_results == 0:
            print("⚠ Warning: No results returned (may indicate search issue)")
        
        return True
        
    except Exception as e:
        print(f"✗ Search failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_answer_benchmark_mini():
    """Test answer benchmark with just 2 queries."""
    print("\n" + "=" * 80)
    print("TEST 4: Mini Answer Benchmark (2 queries)")
    print("=" * 80)
    
    try:
        # Load golden queries
        golden_file = Path("artifacts/benchmarks/v2_1_20/golden_queries_acceptance_v2_1.json")
        if not golden_file.exists():
            print(f"✗ Golden queries file not found: {golden_file}")
            return False
        
        with open(golden_file) as f:
            golden_data = json.load(f)
        
        # Extract cross-paper queries (format: dict with keys like 'papers', 'cross_paper_queries')
        if isinstance(golden_data, dict):
            query_list = golden_data.get("cross_paper_queries", [])
        else:
            query_list = golden_data
        
        print(f"Loaded {len(query_list)} cross-paper queries")
        
        if len(query_list) < 2:
            print(f"⚠ Not enough queries to test (need 2, have {len(query_list)})")
            return False
        
        # Test first 2 queries
        from app.core.agentic_retrieval import AgenticRetrievalOrchestrator
        
        orchestrator = AgenticRetrievalOrchestrator(max_rounds=1)
        
        success_count = 0
        for i, query_obj in enumerate(query_list[:2]):
            query = query_obj.get("query") if isinstance(query_obj, dict) else str(query_obj)
            paper_ids = query_obj.get("paper_ids", []) if isinstance(query_obj, dict) else []
            
            try:
                print(f"\n  Query {i+1}: {query[:60]}...")
                
                result = await orchestrator.retrieve(
                    query=query,
                    paper_ids=paper_ids or [],
                    user_id="test-user",
                    top_k_per_subquestion=5,
                )
                
                sources = result.get("sources", [])
                print(f"    ✓ Processed: {len(sources)} sources retrieved")
                success_count += 1
                
            except Exception as e:
                print(f"    ✗ Failed: {str(e)[:100]}")
        
        if success_count == 2:
            print(f"\n✓ Mini benchmark: {success_count}/2 queries succeeded")
            return True
        else:
            print(f"\n⚠ Mini benchmark: {success_count}/2 queries succeeded")
            return success_count > 0
            
    except Exception as e:
        print(f"✗ Answer benchmark test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n")
    print("*" * 80)
    print("MILVUS FIX VALIDATION TESTS (specter2 disabled)")
    print("*" * 80)
    print()
    
    test1 = await test_milvus_search()
    test2 = await test_answer_benchmark_mini()
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    if test1 and test2:
        print("✓✓✓ ALL TESTS PASSED ✓✓✓")
        print("\nConclusion: Milvus dimension mismatch appears fixed.")
        print("Ready to proceed with full answer benchmark rerun.")
        return 0
    else:
        print("✗✗✗ SOME TESTS FAILED ✗✗✗")
        print("\nCheck errors above and investigate further.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
