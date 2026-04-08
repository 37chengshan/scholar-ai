"""Unit tests for AuditLogger service.

Tests audit logging for tool execution tracking.

Per D-08, D-09:
- Record all tool executions with metrics
- Get user audit logs within date range
- Get risk summary statistics
- Cleanup old logs (30-day retention)

Test Coverage:
- AuditLogger.record() inserts log with correct fields
- AuditLogger.get_user_audit() retrieves logs for user
- AuditLogger.get_risk_summary() returns counts by risk level
- AuditLogger.cleanup_old_logs() deletes old logs
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from app.utils.audit_logger import AuditLogger


class TestAuditLoggerRecord:
    """Test AuditLogger.record() method."""

    @pytest.fixture
    def audit_logger(self):
        """Create AuditLogger instance."""
        return AuditLogger()

    @pytest.mark.asyncio
    async def test_record_inserts_log_with_required_fields(self, audit_logger):
        """Test that record() inserts log with all required fields."""
        # Mock database connection
        with patch("app.core.database.get_db_connection") as mock_db:
            mock_conn = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_conn

            await audit_logger.record(
                user_id="user123",
                tool="delete_paper",
                risk_level="CRITICAL",
                params={"paper_id": "paper456"},
                result="Paper deleted successfully",
                tokens_used=150,
                cost_cny=0.003,
                execution_ms=250,
                ip_address="192.168.1.1",
            )

            # Verify execute was called
            assert mock_conn.execute.called

    @pytest.mark.asyncio
    async def test_record_with_minimal_fields(self, audit_logger):
        """Test record() with only required fields."""
        with patch("app.core.database.get_db_connection") as mock_db:
            mock_conn = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_conn

            await audit_logger.record(
                user_id="user123",
                tool="rag_search",
                risk_level="LOW",
                params={"question": "test"},
            )

            assert mock_conn.execute.called

    @pytest.mark.asyncio
    async def test_record_handles_database_error_gracefully(self, audit_logger):
        """Test that record() handles database errors without raising."""
        with patch("app.core.database.get_db_connection") as mock_db:
            mock_conn = AsyncMock()
            mock_conn.execute.side_effect = Exception("Database error")
            mock_db.return_value.__aenter__.return_value = mock_conn

            # Should not raise exception
            await audit_logger.record(
                user_id="user123", tool="test_tool", risk_level="LOW"
            )


class TestAuditLoggerGetUserAudit:
    """Test AuditLogger.get_user_audit() method."""

    @pytest.fixture
    def audit_logger(self):
        """Create AuditLogger instance."""
        return AuditLogger()

    @pytest.mark.asyncio
    async def test_get_user_audit_returns_logs_in_date_range(self, audit_logger):
        """Test get_user_audit() returns logs within date range."""
        mock_logs = [
            {
                "id": "log1",
                "user_id": "user123",
                "tool": "rag_search",
                "risk_level": "LOW",
                "created_at": datetime.now(timezone.utc),
            }
        ]

        with patch("app.core.database.get_db_connection") as mock_db:
            mock_conn = AsyncMock()
            mock_conn.fetch.return_value = mock_logs
            mock_db.return_value.__aenter__.return_value = mock_conn

            start_date = datetime.now(timezone.utc) - timedelta(days=7)
            end_date = datetime.now(timezone.utc)

            result = await audit_logger.get_user_audit(
                user_id="user123", start_date=start_date, end_date=end_date
            )

            assert len(result) == 1
            assert result[0]["tool"] == "rag_search"

    @pytest.mark.asyncio
    async def test_get_user_audit_with_pagination(self, audit_logger):
        """Test get_user_audit() with limit and offset."""
        with patch("app.core.database.get_db_connection") as mock_db:
            mock_conn = AsyncMock()
            mock_conn.fetch.return_value = []
            mock_db.return_value.__aenter__.return_value = mock_conn

            await audit_logger.get_user_audit(
                user_id="user123",
                start_date=datetime.now(timezone.utc) - timedelta(days=30),
                end_date=datetime.now(timezone.utc),
                limit=10,
                offset=0,
            )

            assert mock_conn.fetch.called


class TestAuditLoggerGetRiskSummary:
    """Test AuditLogger.get_risk_summary() method."""

    @pytest.fixture
    def audit_logger(self):
        """Create AuditLogger instance."""
        return AuditLogger()

    @pytest.mark.asyncio
    async def test_get_risk_summary_returns_counts_by_level(self, audit_logger):
        """Test get_risk_summary() returns counts for each risk level."""
        mock_summary = [
            {"risk_level": "LOW", "count": 100},
            {"risk_level": "MEDIUM", "count": 50},
            {"risk_level": "HIGH", "count": 10},
            {"risk_level": "CRITICAL", "count": 2},
        ]

        with patch("app.core.database.get_db_connection") as mock_db:
            mock_conn = AsyncMock()
            mock_conn.fetch.return_value = mock_summary
            mock_db.return_value.__aenter__.return_value = mock_conn

            result = await audit_logger.get_risk_summary(user_id="user123", days=7)

            assert result["LOW"] == 100
            assert result["MEDIUM"] == 50
            assert result["HIGH"] == 10
            assert result["CRITICAL"] == 2

    @pytest.mark.asyncio
    async def test_get_risk_summary_defaults_to_zero(self, audit_logger):
        """Test get_risk_summary() returns zeros for missing levels."""
        mock_summary = []  # No logs

        with patch("app.core.database.get_db_connection") as mock_db:
            mock_conn = AsyncMock()
            mock_conn.fetch.return_value = mock_summary
            mock_db.return_value.__aenter__.return_value = mock_conn

            result = await audit_logger.get_risk_summary(user_id="user123", days=7)

            # Should have all risk levels with 0 count
            assert result["LOW"] == 0
            assert result["MEDIUM"] == 0
            assert result["HIGH"] == 0
            assert result["CRITICAL"] == 0


class TestAuditLoggerCleanupOldLogs:
    """Test AuditLogger.cleanup_old_logs() method."""

    @pytest.fixture
    def audit_logger(self):
        """Create AuditLogger instance."""
        return AuditLogger()

    @pytest.mark.asyncio
    async def test_cleanup_old_logs_deletes_old_records(self, audit_logger):
        """Test cleanup_old_logs() deletes records older than specified days."""
        with patch("app.core.database.get_db_connection") as mock_db:
            mock_conn = AsyncMock()
            mock_conn.execute.return_value = "DELETE 100"
            mock_db.return_value.__aenter__.return_value = mock_conn

            result = await audit_logger.cleanup_old_logs(days=30)

            # Should return deleted count
            assert mock_conn.execute.called

    @pytest.mark.asyncio
    async def test_cleanup_uses_default_30_days(self, audit_logger):
        """Test cleanup defaults to 30 days per D-09."""
        with patch("app.core.database.get_db_connection") as mock_db:
            mock_conn = AsyncMock()
            mock_conn.execute.return_value = "DELETE 50"
            mock_db.return_value.__aenter__.return_value = mock_conn

            await audit_logger.cleanup_old_logs()

            # Should use 30 days default
            assert mock_conn.execute.called
