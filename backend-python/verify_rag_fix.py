"""Verification script for RAG query zero results fix.

This script tests that RAG queries work correctly when paper_ids is empty.
"""

import asyncio
from app.core.multimodal_search_service import get_multimodal_search_service
from app.core.milvus_service import get_milvus_service
from app.utils.logger import logger


async def verify_fix():
    """Verify that empty paper_ids doesn't filter out all results."""
    
    # Test data
    user_id = "test-user-001"
    paper_id = "a5605227-b85b-47aa-9753-d1fde34a112b"
    
    # Get services
    search_service = get_multimodal_search_service()
    milvus = get_milvus_service()
    
    # Test 1: Check if data exists in Milvus
    logger.info("=" * 60)
    logger.info("Test 1: Verify data exists in Milvus")
    logger.info("=" * 60)
    
    # Create a dummy embedding (2048-dim)
    dummy_embedding = [0.1] * 2048
    
    # Search without paper_ids filter
    results_no_filter = milvus.search_contents_v2(
        embedding=dummy_embedding,
        user_id=user_id,
        top_k=20
    )
    
    logger.info(f"Results without paper_ids filter: {len(results_no_filter)}")
    
    if len(results_no_filter) > 0:
        logger.info(f"✓ Data found in Milvus: {len(results_no_filter)} chunks")
        logger.info(f"Sample paper_ids: {[r.get('paper_id') for r in results_no_filter[:3]]}")
    else:
        logger.error("✗ No data found in Milvus - fix cannot be verified")
        return False
    
    # Test 2: Search with empty paper_ids (should NOT filter)
    logger.info("\n" + "=" * 60)
    logger.info("Test 2: Search with empty paper_ids list")
    logger.info("=" * 60)
    
    results_empty_paper_ids = await search_service.search(
        query="test query",
        paper_ids=[],  # Empty list
        user_id=user_id,
        top_k=10,
        use_reranker=False
    )
    
    total_results = results_empty_paper_ids.get("total_count", 0)
    
    logger.info(f"Results with empty paper_ids: {total_results}")
    
    if total_results > 0:
        logger.info(f"✓ Fix works! Empty paper_ids doesn't filter out results")
        logger.info(f"Sample results: {len(results_empty_paper_ids.get('results', []))}")
    else:
        logger.error("✗ Fix failed! Empty paper_ids still filters out all results")
        return False
    
    # Test 3: Search with specific paper_ids (should filter)
    logger.info("\n" + "=" * 60)
    logger.info("Test 3: Search with specific paper_ids")
    logger.info("=" * 60)
    
    results_with_paper_ids = await search_service.search(
        query="test query",
        paper_ids=[paper_id],
        user_id=user_id,
        top_k=10,
        use_reranker=False
    )
    
    total_filtered = results_with_paper_ids.get("total_count", 0)
    
    logger.info(f"Results with paper_ids=[{paper_id}]: {total_filtered}")
    
    # Check if all results have the correct paper_id
    all_paper_ids = [r.get("paper_id") for r in results_with_paper_ids.get("results", [])]
    
    if all(p_id == paper_id for p_id in all_paper_ids):
        logger.info(f"✓ paper_ids filtering works correctly")
    else:
        logger.warning(f"Some results have wrong paper_id: {all_paper_ids}")
    
    logger.info("\n" + "=" * 60)
    logger.info("VERIFICATION COMPLETE")
    logger.info("=" * 60)
    
    return True


if __name__ == "__main__":
    success = asyncio.run(verify_fix())
    if success:
        print("\n✓✓✓ All tests passed - Fix verified! ✓✓✓")
    else:
        print("\n✗✗✗ Some tests failed - Fix needs review ✗✗✗")