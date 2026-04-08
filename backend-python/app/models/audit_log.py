"""Audit log database model.

Tracks all tool executions with metadata for compliance and debugging.
Per D-08: Records tool_name, risk_level, execution_time_ms, token_usage.
Per D-09: 30-day retention with automatic cleanup.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional
import json

from app.core.database import get_db_connection
from app.utils.logger import logger


# Audit log retention period per D-09
AUDIT_LOG_RETENTION_DAYS = 30


class RiskLevel(Enum):
    """Tool risk levels for safety assessment."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditLog:
    """Audit log entry for tool execution tracking."""
    
    def __init__(
        self,
        id: Optional[int] = None,
        user_id: str = "",
        session_id: str = "",
        tool_name: str = "",
        params: Optional[Dict[str, Any]] = None,
        risk_level: RiskLevel = RiskLevel.LOW,
        execution_time_ms: int = 0,
        token_usage: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        confirmed: bool = False,
        result_summary: str = "",
    ):
        self.id = id
        self.user_id = user_id
        self.session_id = session_id
        self.tool_name = tool_name
        self.params = params or {}
        self.risk_level = risk_level
        self.execution_time_ms = execution_time_ms
        self.token_usage = token_usage or {}
        self.timestamp = timestamp or datetime.utcnow()
        self.confirmed = confirmed
        self.result_summary = result_summary
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "tool_name": self.tool_name,
            "params": self.params,
            "risk_level": self.risk_level.value,
            "execution_time_ms": self.execution_time_ms,
            "token_usage": self.token_usage,
            "timestamp": self.timestamp.isoformat(),
            "confirmed": self.confirmed,
            "result_summary": self.result_summary,
        }
    
    @classmethod
    async def create(
        cls,
        user_id: str,
        session_id: str,
        tool_name: str,
        params: Dict[str, Any],
        risk_level: RiskLevel,
        execution_time_ms: int = 0,
        token_usage: Optional[Dict[str, Any]] = None,
        confirmed: bool = False,
        result_summary: str = "",
    ) -> "AuditLog":
        """Create and persist audit log entry."""
        log_entry = cls(
            user_id=user_id, session_id=session_id, tool_name=tool_name,
            params=params, risk_level=risk_level, execution_time_ms=execution_time_ms,
            token_usage=token_usage, confirmed=confirmed, result_summary=result_summary,
        )
        
        try:
            async with get_db_connection() as conn:
                await conn.execute(
                    """INSERT INTO audit_logs (
                        user_id, session_id, tool_name, params,
                        risk_level, execution_time_ms, token_usage,
                        confirmed, result_summary, timestamp
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)""",
                    user_id, session_id, tool_name, json.dumps(params),
                    risk_level.value, execution_time_ms, json.dumps(token_usage or {}),
                    1 if confirmed else 0, result_summary, log_entry.timestamp,
                )
                row = await conn.fetchrow("SELECT currval('audit_logs_id_seq') as id")
                if row:
                    log_entry.id = row["id"]
                logger.info("Audit log created", log_id=log_entry.id, tool=tool_name)
        except Exception as e:
            logger.error("Failed to create audit log", error=str(e))
        
        return log_entry
    
    @classmethod
    async def cleanup_old_logs(cls, retention_days: int = AUDIT_LOG_RETENTION_DAYS) -> int:
        """Delete audit logs older than retention period."""
        try:
            async with get_db_connection() as conn:
                cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
                count_result = await conn.fetchrow(
                    "SELECT COUNT(*) as count FROM audit_logs WHERE timestamp < $1",
                    cutoff_date,
                )
                count = count_result["count"] if count_result else 0
                if count > 0:
                    await conn.execute(
                        "DELETE FROM audit_logs WHERE timestamp < $1", cutoff_date
                    )
                    logger.info("Audit logs cleaned up", deleted_count=count)
                return count
        except Exception as e:
            logger.error("Failed to cleanup audit logs", error=str(e))
            return 0


# Tool risk mapping per D-07
TOOL_RISK_MAPPING: Dict[str, RiskLevel] = {
    "delete_paper": RiskLevel.CRITICAL,
    "execute_command": RiskLevel.CRITICAL,
    "upload_paper": RiskLevel.HIGH,
    "create_note": RiskLevel.MEDIUM,
    "update_note": RiskLevel.MEDIUM,
    "merge_documents": RiskLevel.MEDIUM,
    "external_search": RiskLevel.LOW,
    "rag_search": RiskLevel.LOW,
    "list_papers": RiskLevel.LOW,
    "read_paper": RiskLevel.LOW,
    "list_notes": RiskLevel.LOW,
    "read_note": RiskLevel.LOW,
    "extract_references": RiskLevel.LOW,
    "ask_user_confirmation": RiskLevel.LOW,
    "show_message": RiskLevel.LOW,
}


def get_tool_risk_level(tool_name: str) -> RiskLevel:
    return TOOL_RISK_MAPPING.get(tool_name, RiskLevel.MEDIUM)


def requires_confirmation(tool_name: str) -> bool:
    return get_tool_risk_level(tool_name) == RiskLevel.CRITICAL


__all__ = ["AuditLog", "RiskLevel", "AUDIT_LOG_RETENTION_DAYS", "TOOL_RISK_MAPPING", "get_tool_risk_level", "requires_confirmation"]
