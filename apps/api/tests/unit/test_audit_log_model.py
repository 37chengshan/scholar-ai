"""Unit tests for the current SQLAlchemy AuditLog model."""

from app.models.orm_audit_log import AuditLog
from app.models.user import User


class TestAuditLogModel:
    def test_audit_log_model_exists_in_orm(self):
        assert AuditLog.__tablename__ == "audit_logs"

    def test_audit_log_has_required_fields(self):
        columns = AuditLog.__table__.columns.keys()

        for field in ["id", "user_id", "tool", "risk_level", "created_at"]:
            assert field in columns

    def test_audit_log_has_performance_metrics(self):
        columns = AuditLog.__table__.columns.keys()

        assert "tokens_used" in columns
        assert "cost_cny" in columns
        assert "execution_ms" in columns

    def test_audit_log_has_user_relation(self):
        assert "user" in AuditLog.__mapper__.relationships.keys()
        assert AuditLog.__mapper__.relationships["user"].mapper.class_ is User

    def test_audit_log_has_indexes(self):
        index_names = {index.name for index in AuditLog.__table__.indexes}

        assert "idx_audit_logs_user_id" in index_names
        assert "idx_audit_logs_created_at" in index_names
        assert "idx_audit_logs_risk_level" in index_names


class TestAuditLogUserRelation:
    def test_user_model_has_audit_logs_relation(self):
        assert "audit_logs" in User.__mapper__.relationships.keys()
        assert User.__mapper__.relationships["audit_logs"].mapper.class_ is AuditLog
