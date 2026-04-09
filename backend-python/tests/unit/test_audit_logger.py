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
        # Mock AsyncSessionLocal
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        with patch("app.utils.audit_logger.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session

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

            # Verify add was called with AuditLog object
            assert mock_session.add.called
            added_obj = mock_session.add.call_args[0][0]
            assert added_obj.user_id == "user123"
            assert added_obj.tool == "delete_paper"
            assert added_obj.risk_level == "CRITICAL"

    @pytest.mark.asyncio
    async def test_record_with_minimal_fields(self, audit_logger):
        """Test record() with only required fields."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        with patch("app.utils.audit_logger.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session

            await audit_logger.record(
                user_id="user123",
                tool="rag_search",
                risk_level="LOW",
                params={"question": "test"},
            )

            assert mock_session.add.called
            added_obj = mock_session.add.call_args[0][0]
            assert added_obj.tool == "rag_search"
            assert added_obj.risk_level == "LOW"

    @pytest.mark.asyncio
    async def test_record_handles_database_error_gracefully(self, audit_logger):
        """Test that record() handles database errors without raising."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush.side_effect = Exception("Database error")

        with patch("app.utils.audit_logger.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session

            # Should not raise exception, returns False
            result = await audit_logger.record(
                user_id="user123", tool="test_tool", risk_level="LOW"
            )

            assert result is False


class TestAuditLoggerGetUserAudit:
    """Test AuditLogger.get_user_audit() method."""

    @pytest.fixture
    def audit_logger(self):
        """Create AuditLogger instance."""
        return AuditLogger()

    @pytest.mark.asyncio
    async def test_get_user_audit_returns_logs_in_date_range(self, audit_logger):
        """Test get_user_audit() returns logs within date range."""
        # Create mock AuditLog objects
        mock_log = MagicMock()
        mock_log.id = "log1"
        mock_log.user_id = "user123"
        mock_log.tool = "rag_search"
        mock_log.risk_level = "LOW"
        mock_log.params = None
        mock_log.result = None
        mock_log.tokens_used = None
        mock_log.cost_cny = None
        mock_log.execution_ms = None
        mock_log.ip_address = None
        mock_log.created_at = datetime.now(timezone.utc)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_log]

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        with patch("app.utils.audit_logger.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session

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
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        with patch("app.utils.audit_logger.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session

            await audit_logger.get_user_audit(
                user_id="user123",
                start_date=datetime.now(timezone.utc) - timedelta(days=30),
                end_date=datetime.now(timezone.utc),
                limit=10,
                offset=0,
            )

            assert mock_session.execute.called


class TestAuditLoggerGetRiskSummary:
    """Test AuditLogger.get_risk_summary() method."""

    @pytest.fixture
    def audit_logger(self):
        """Create AuditLogger instance."""
        return AuditLogger()

    @pytest.mark.asyncio
    async def test_get_risk_summary_returns_counts_by_level(self, audit_logger):
        """Test get_risk_summary() returns counts for each risk level."""
        # Mock rows with risk_level and count
        mock_rows = [
            MagicMock(risk_level="LOW", count=100),
            MagicMock(risk_level="MEDIUM", count=50),
            MagicMock(risk_level="HIGH", count=10),
            MagicMock(risk_level="CRITICAL", count=2),
        ]

        mock_result = MagicMock()
        mock_result.all.return_value = mock_rows

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        with patch("app.utils.audit_logger.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session

            result = await audit_logger.get_risk_summary(user_id="user123", days=7)

            assert result["LOW"] == 100
            assert result["MEDIUM"] == 50
            assert result["HIGH"] == 10
            assert result["CRITICAL"] == 2

    @pytest.mark.asyncio
    async def test_get_risk_summary_defaults_to_zero(self, audit_logger):
        """Test get_risk_summary() returns zeros for missing levels."""
        mock_result = MagicMock()
        mock_result.all.return_value = []  # No logs

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result

        with patch("app.utils.audit_logger.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session

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
        # Mock count result
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 100

        mock_session = AsyncMock()
        mock_session.execute.side_effect = [mock_count_result, None]

        with patch("app.utils.audit_logger.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session

            result = await audit_logger.cleanup_old_logs(days=30)

            # Should return deleted count
            assert result == 100
            assert mock_session.execute.call_count == 2  # count + delete

    @pytest.mark.asyncio
    async def test_cleanup_uses_default_30_days(self, audit_logger):
        """Test cleanup defaults to 30 days per D-09."""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 50

        mock_session = AsyncMock()
        mock_session.execute.side_effect = [mock_count_result, None]

        with patch("app.utils.audit_logger.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session

            result = await audit_logger.cleanup_old_logs()

            # Should use 30 days default and return deleted count
            assert result == 50

    @pytest.mark.asyncio
    async def test_cleanup_skips_delete_if_count_zero(self, audit_logger):
        """Test cleanup skips delete if no records to delete."""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_count_result

        with patch("app.utils.audit_logger.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session

            result = await audit_logger.cleanup_old_logs(days=30)

            # Should return 0 and only call execute once (count only)
            assert result == 0
            assert mock_session.execute.call_count == 1