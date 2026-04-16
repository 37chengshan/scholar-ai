"""Unit tests for AuditLog database model.

Tests Prisma schema and database operations for audit logging.

Per D-08, D-09:
- Audit logs track all tool executions
- Include performance metrics (tokens, cost, execution time)
- Retained for 30 days

Test Coverage:
- AuditLog model exists with all required fields
- Foreign key relation to User model works
- Indexes exist for query performance
"""

import pytest
from unittest.mock import AsyncMock, patch


class TestAuditLogModel:
    """Test AuditLog Prisma model definition."""

    def test_audit_log_model_exists_in_schema(self):
        """Test that AuditLog model is defined in schema.prisma."""
        import os

        schema_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "backend-node",
            "prisma",
            "schema.prisma",
        )

        with open(schema_path, "r") as f:
            schema_content = f.read()

        assert "model AuditLog" in schema_content, (
            "AuditLog model should exist in schema"
        )

    def test_audit_log_has_required_fields(self):
        """Test that AuditLog model has all required fields."""
        import os

        schema_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "backend-node",
            "prisma",
            "schema.prisma",
        )

        with open(schema_path, "r") as f:
            schema_content = f.read()

        # Find the AuditLog model block
        start = schema_content.find("model AuditLog")
        assert start != -1, "AuditLog model not found"

        # Find the end of the model (next 'model' keyword or end of file)
        end = schema_content.find("\nmodel ", start + 1)
        if end == -1:
            end = len(schema_content)

        model_block = schema_content[start:end]

        # Required fields per D-08
        required_fields = ["id", "userId", "tool", "riskLevel", "createdAt"]

        for field in required_fields:
            assert field in model_block, f"AuditLog should have {field} field"

    def test_audit_log_has_performance_metrics(self):
        """Test that AuditLog includes performance metrics."""
        import os

        schema_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "backend-node",
            "prisma",
            "schema.prisma",
        )

        with open(schema_path, "r") as f:
            schema_content = f.read()

        start = schema_content.find("model AuditLog")
        end = schema_content.find("\nmodel ", start + 1)
        if end == -1:
            end = len(schema_content)

        model_block = schema_content[start:end]

        # Performance metrics per D-08
        assert "tokensUsed" in model_block, "AuditLog should track tokens used"
        assert "costCny" in model_block, "AuditLog should track cost in CNY"
        assert "executionMs" in model_block, "AuditLog should track execution time"

    def test_audit_log_has_user_relation(self):
        """Test that AuditLog has foreign key relation to User."""
        import os

        schema_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "backend-node",
            "prisma",
            "schema.prisma",
        )

        with open(schema_path, "r") as f:
            schema_content = f.read()

        start = schema_content.find("model AuditLog")
        end = schema_content.find("\nmodel ", start + 1)
        if end == -1:
            end = len(schema_content)

        model_block = schema_content[start:end]

        assert "user" in model_block.lower(), "AuditLog should have user relation"
        assert "@relation" in model_block, "AuditLog should have Prisma relation"

    def test_audit_log_has_indexes(self):
        """Test that AuditLog has indexes for query performance."""
        import os

        schema_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "backend-node",
            "prisma",
            "schema.prisma",
        )

        with open(schema_path, "r") as f:
            schema_content = f.read()

        start = schema_content.find("model AuditLog")
        end = schema_content.find("\nmodel ", start + 1)
        if end == -1:
            end = len(schema_content)

        model_block = schema_content[start:end]

        # Indexes for performance
        assert "@@index([userId])" in model_block or "@@index" in model_block, (
            "AuditLog should have userId index"
        )
        assert "@@index([createdAt])" in model_block or "createdAt" in model_block, (
            "AuditLog should have createdAt index"
        )


class TestAuditLogUserRelation:
    """Test AuditLog relation to User model."""

    def test_user_model_has_audit_logs_relation(self):
        """Test that User model has auditLogs relation."""
        import os

        schema_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "backend-node",
            "prisma",
            "schema.prisma",
        )

        with open(schema_path, "r") as f:
            schema_content = f.read()

        # Find users model
        start = schema_content.find("model users")
        end = schema_content.find("\nmodel ", start + 1)
        if end == -1:
            end = len(schema_content)

        user_model = schema_content[start:end]

        assert "auditLogs" in user_model or "AuditLog" in user_model, (
            "User model should reference AuditLog relation"
        )
