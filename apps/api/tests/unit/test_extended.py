"""Extended API tests for Phase 27-04 endpoints.

Tests cover:
- Notes CRUD operations
- Projects CRUD operations
- Annotations CRUD operations
- Reading progress tracking
- Dashboard stats
- System health
- Search functionality
- Session management
- Entities and graph
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# =============================================================================
# Router Import Tests
# =============================================================================

class TestRouterImports:
    """Tests to verify all routers can be imported."""

    def test_import_notes_router(self):
        """Test that notes router can be imported."""
        from app.api.notes import router
        assert router is not None
        assert len(router.routes) > 0

    def test_import_projects_router(self):
        """Test that projects router can be imported."""
        from app.api.projects import router
        assert router is not None
        assert len(router.routes) > 0

    def test_import_annotations_router(self):
        """Test that annotations router can be imported."""
        from app.api.annotations import router
        assert router is not None
        assert len(router.routes) > 0

    def test_import_reading_progress_router(self):
        """Test that reading_progress router can be imported."""
        from app.api.reading_progress import router
        assert router is not None
        assert len(router.routes) > 0

    def test_import_dashboard_router(self):
        """Test that dashboard router can be imported."""
        from app.api.dashboard import router
        assert router is not None
        assert len(router.routes) > 0

    def test_import_system_router(self):
        """Test that system router can be imported."""
        from app.api.system import router
        assert router is not None
        assert len(router.routes) > 0

    def test_import_search_router(self):
        """Test that search router can be imported."""
        from app.api.search import router
        assert router is not None
        assert len(router.routes) > 0

    def test_import_semantic_scholar_router(self):
        """Test that semantic_scholar router can be imported."""
        from app.api.semantic_scholar import router
        assert router is not None
        assert len(router.routes) > 0

    def test_import_session_router(self):
        """Test that session router can be imported."""
        from app.api.session import router
        assert router is not None
        assert len(router.routes) > 0

    def test_import_chat_router(self):
        """Test that chat router can be imported."""
        from app.api.chat import router
        assert router is not None
        assert len(router.routes) > 0

    def test_import_entities_router(self):
        """Test that entities router can be imported."""
        from app.api.entities import router
        assert router is not None
        assert len(router.routes) > 0

    def test_import_graph_router(self):
        """Test that graph router can be imported."""
        from app.api.graph import router
        assert router is not None
        assert len(router.routes) > 0

    def test_import_compare_router(self):
        """Test that compare router can be imported."""
        from app.api.compare import router
        assert router is not None
        assert len(router.routes) > 0

    def test_import_health_router(self):
        """Test that health router can be imported."""
        from app.api.health import router
        assert router is not None
        assert len(router.routes) > 0


# =============================================================================
# Notes Model Tests
# =============================================================================

class TestNotesModels:
    """Tests for notes request/response models."""

    def test_note_create_model(self):
        """Test NoteCreate model validation."""
        from app.api.notes import NoteCreate

        note = NoteCreate(
            title="Test Note",
            content="Test content",
            tags=["test"],
            paperIds=["paper-1"]
        )

        assert note.title == "Test Note"
        assert note.content == "Test content"
        assert note.tags == ["test"]
        assert note.paperIds == ["paper-1"]

    def test_note_update_model(self):
        """Test NoteUpdate model validation."""
        from app.api.notes import NoteUpdate

        update = NoteUpdate(title="Updated Title")
        assert update.title == "Updated Title"
        assert update.content is None

    def test_generate_notes_request_model(self):
        """Test GenerateNotesRequest model."""
        from app.api.notes import GenerateNotesRequest

        req = GenerateNotesRequest(paper_id="paper-123")
        assert req.paper_id == "paper-123"


# =============================================================================
# Projects Model Tests
# =============================================================================

class TestProjectsModels:
    """Tests for projects request/response models."""

    def test_project_create_model(self):
        """Test ProjectCreate model validation."""
        from app.api.projects import ProjectCreate

        project = ProjectCreate(name="Test Project", color="#3B82F6")
        assert project.name == "Test Project"
        assert project.color == "#3B82F6"

    def test_project_create_default_color(self):
        """Test ProjectCreate with default color."""
        from app.api.projects import ProjectCreate

        project = ProjectCreate(name="Test Project")
        assert project.color == "#3B82F6"

    def test_project_update_model(self):
        """Test ProjectUpdate model validation."""
        from app.api.projects import ProjectUpdate

        update = ProjectUpdate(name="Updated Name")
        assert update.name == "Updated Name"
        assert update.color is None


# =============================================================================
# Annotations Model Tests
# =============================================================================

class TestAnnotationsModels:
    """Tests for annotations request/response models."""

    def test_annotation_create_model(self):
        """Test AnnotationCreate model validation."""
        from app.api.annotations import AnnotationCreate

        annotation = AnnotationCreate(
            paperId="paper-1",
            type="highlight",
            pageNumber=1,
            position={"x": 0, "y": 0},
            content="Test annotation",
            color="#FFEB3B"
        )

        assert annotation.paperId == "paper-1"
        assert annotation.type == "highlight"
        assert annotation.pageNumber == 1

    def test_annotation_update_model(self):
        """Test AnnotationUpdate model validation."""
        from app.api.annotations import AnnotationUpdate

        update = AnnotationUpdate(content="Updated content")
        assert update.content == "Updated content"
        assert update.color is None


# =============================================================================
# Reading Progress Model Tests
# =============================================================================

class TestReadingProgressModels:
    """Tests for reading progress request/response models."""

    def test_progress_create_model(self):
        """Test ProgressCreate model validation."""
        from app.api.reading_progress import ProgressCreate

        progress = ProgressCreate(currentPage=5, totalPages=20)
        assert progress.currentPage == 5
        assert progress.totalPages == 20


# =============================================================================
# Dashboard Model Tests
# =============================================================================

class TestDashboardModels:
    """Tests for dashboard response models."""

    def test_dashboard_stats_model(self):
        """Test DashboardStats model."""
        from app.api.dashboard import DashboardStats

        stats = DashboardStats(
            totalPapers=100,
            starredPapers=10,
            processingPapers=5,
            completedPapers=85,
            queriesCount=500,
            sessionsCount=50,
            projectsCount=10,
            llmTokens=10000
        )

        assert stats.totalPapers == 100
        assert stats.starredPapers == 10

    def test_data_point_model(self):
        """Test DataPoint model."""
        from app.api.dashboard import DataPoint

        point = DataPoint(date="2024-01-01", papers=5, queries=10)
        assert point.date == "2024-01-01"
        assert point.papers == 5


# =============================================================================
# System Endpoint Tests
# =============================================================================

class TestSystemEndpoints:
    """Tests for system endpoint functions."""

    @pytest.mark.asyncio
    async def test_storage_endpoint_logic(self):
        """Test storage endpoint returns valid structure."""
        from app.api.system import get_storage_info

        # Mock database connection
        with patch("app.api.system.get_db_connection") as mock_conn:
            mock_conn.return_value.__aenter__ = AsyncMock()
            mock_conn.return_value.__aenter__.return_value.fetchval = AsyncMock(return_value=10)

            result = await get_storage_info()

            assert result.success is True
            assert "vectorDB" in result.data
            assert "fileStorage" in result.data


# =============================================================================
# Search Model Tests
# =============================================================================

class TestSearchModels:
    """Tests for search request/response models."""

    def test_search_result_model(self):
        """Test SearchResult model."""
        from app.api.search import SearchResult

        result = SearchResult(
            id="paper-1",
            title="Test Paper",
            authors=["Author 1"],
            year=2024,
            abstract="Test abstract",
            source="arxiv",
            url="https://example.com/paper"
        )

        assert result.id == "paper-1"
        assert result.title == "Test Paper"

    def test_library_search_result_model(self):
        """Test LibrarySearchResult model."""
        from app.api.search import LibrarySearchResult

        result = LibrarySearchResult(
            id="chunk-1",
            paper_id="paper-1",
            content="Test content",
            rrf_score=0.95
        )

        assert result.id == "chunk-1"
        assert result.rrf_score == 0.95


# =============================================================================
# Semantic Scholar Model Tests
# =============================================================================

class TestSemanticScholarModels:
    """Tests for Semantic Scholar endpoint functionality."""

    def test_router_has_batch_endpoint(self):
        """Test that batch endpoint is defined."""
        from app.api.semantic_scholar import router

        routes = [r.path for r in router.routes]
        assert "/batch" in routes

    def test_router_has_autocomplete_endpoint(self):
        """Test that autocomplete endpoint is defined."""
        from app.api.semantic_scholar import router

        routes = [r.path for r in router.routes]
        assert "/autocomplete" in routes

    def test_router_has_author_search_endpoint(self):
        """Test that author search endpoint is defined."""
        from app.api.semantic_scholar import router

        routes = [r.path for r in router.routes]
        assert "/author/search" in routes


# =============================================================================
# Session Model Tests
# =============================================================================

class TestSessionModels:
    """Tests for session models."""

    def test_session_create_model(self):
        """Test SessionCreate model."""
        from app.schemas.session import SessionCreate

        session = SessionCreate(title="Test Session")
        assert session.title == "Test Session"

    def test_session_update_model(self):
        """Test SessionUpdate model."""
        from app.schemas.session import SessionUpdate

        update = SessionUpdate(title="Updated Session")
        assert update.title == "Updated Session"


# =============================================================================
# Entities Model Tests
# =============================================================================

class TestEntitiesModels:
    """Tests for entity models."""

    def test_entity_extraction_request_model(self):
        """Test EntityExtractionRequest model."""
        from app.api.entities import EntityExtractionRequest

        req = EntityExtractionRequest(
            text="Test text for extraction",
            entity_types=["method", "dataset"]
        )

        assert req.text == "Test text for extraction"
        assert "method" in req.entity_types

    def test_build_graph_request_model(self):
        """Test BuildGraphRequest model."""
        from app.api.entities import BuildGraphRequest

        req = BuildGraphRequest(
            paper_text="Full paper text",
            authors=["Author 1"],
            references=[{"id": "ref-1"}]
        )

        assert req.paper_text == "Full paper text"


# =============================================================================
# Graph Model Tests
# =============================================================================

class TestGraphModels:
    """Tests for graph models."""

    def test_graph_node_model(self):
        """Test GraphNode model."""
        from app.api.graph import GraphNode

        node = GraphNode(
            id="node-1",
            name="Test Node",
            type="Paper",
            pagerank=0.5
        )

        assert node.id == "node-1"
        assert node.pagerank == 0.5

    def test_graph_edge_model(self):
        """Test GraphEdge model."""
        from app.api.graph import GraphEdge

        edge = GraphEdge(
            source="node-1",
            target="node-2",
            type="CITES"
        )

        assert edge.source == "node-1"
        assert edge.type == "CITES"


# =============================================================================
# Compare Model Tests
# =============================================================================

class TestCompareModels:
    """Tests for compare models."""

    def test_compare_request_model(self):
        """Test CompareRequest model."""
        from app.api.compare import CompareRequest

        req = CompareRequest(
            paper_ids=["paper-1", "paper-2"],
            dimensions=["method", "results"]
        )

        assert len(req.paper_ids) == 2
        assert "method" in req.dimensions

    def test_evolution_request_model(self):
        """Test EvolutionRequest model."""
        from app.api.compare import EvolutionRequest

        req = EvolutionRequest(
            paper_ids=["paper-1", "paper-2"],
            method_name="YOLO"
        )

        assert req.method_name == "YOLO"


# =============================================================================
# Route Count Tests
# =============================================================================

class TestRouteCounts:
    """Tests to verify expected number of routes per router."""

    def test_notes_route_count(self):
        """Test notes router has expected routes."""
        from app.api.notes import router

        routes = [r.path for r in router.routes]
        # Should have: POST, GET list, GET :id, PUT :id, DELETE :id, GET paper/:id, POST generate, POST regenerate, GET :id/export
        assert len(routes) >= 6

    def test_projects_route_count(self):
        """Test projects router has expected routes."""
        from app.api.projects import router

        routes = [r.path for r in router.routes]
        # Should have: GET list, POST, GET :id, PATCH :id, DELETE :id, PATCH paper/:paperId
        assert len(routes) >= 5

    def test_annotations_route_count(self):
        """Test annotations router has expected routes."""
        from app.api.annotations import router

        routes = [r.path for r in router.routes]
        # Should have: GET :paperId, POST, PATCH :id, DELETE :id
        assert len(routes) >= 4

    def test_reading_progress_route_count(self):
        """Test reading_progress router has expected routes."""
        from app.api.reading_progress import router

        routes = [r.path for r in router.routes]
        # Should have: GET, GET :paperId, POST :paperId
        assert len(routes) >= 3

    def test_dashboard_route_count(self):
        """Test dashboard router has expected routes."""
        from app.api.dashboard import router

        routes = [r.path for r in router.routes]
        # Should have: /stats, /trends, /recent-papers, /reading-stats
        assert len(routes) >= 4

    def test_system_route_count(self):
        """Test system router has expected routes."""
        from app.api.system import router

        routes = [r.path for r in router.routes]
        # Should have: /storage, /logs/stream, /health
        assert len(routes) >= 3


# =============================================================================
# Total Router Count Test
# =============================================================================

class TestTotalRouters:
    """Tests for total router count."""

    def test_all_routers_exist(self):
        """Test that all 14 routers exist and have routes."""
        from app.api.notes import router as notes_router
        from app.api.projects import router as projects_router
        from app.api.annotations import router as annotations_router
        from app.api.reading_progress import router as reading_progress_router
        from app.api.dashboard import router as dashboard_router
        from app.api.system import router as system_router
        from app.api.search import router as search_router
        from app.api.semantic_scholar import router as ss_router
        from app.api.session import router as session_router
        from app.api.chat import router as chat_router
        from app.api.entities import router as entities_router
        from app.api.graph import router as graph_router
        from app.api.compare import router as compare_router
        from app.api.health import router as health_router

        routers = [
            ("notes", notes_router),
            ("projects", projects_router),
            ("annotations", annotations_router),
            ("reading_progress", reading_progress_router),
            ("dashboard", dashboard_router),
            ("system", system_router),
            ("search", search_router),
            ("semantic_scholar", ss_router),
            ("session", session_router),
            ("chat", chat_router),
            ("entities", entities_router),
            ("graph", graph_router),
            ("compare", compare_router),
            ("health", health_router)
        ]

        for name, router in routers:
            assert router is not None, f"{name} router is None"
            assert len(router.routes) > 0, f"{name} router has no routes"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])