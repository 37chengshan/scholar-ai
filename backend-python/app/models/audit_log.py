"""Audit log database model using SQLAlchemy ORM.

Tracks all tool executions with metadata for compliance and debugging.
Per D-08: Records tool_name, risk_level, execution_time_ms, token_usage.
Per D-09: 30-day retention with automatic cleanup.

Schema matches Prisma model 'AuditLog' in audit_logs table.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.orm_audit_log import AuditLog as AuditLogORM
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
    """Audit log entry for tool execution tracking.

    This is a service layer class that wraps the SQLAlchemy ORM model
    and provides business logic methods for creating and managing audit logs.
    """

    def __init__(
        self,
        id: Optional[str] = None,
        user_id: str = "",
        tool: str = "",
        params: Optional[Dict[str, Any]] = None,
        risk_level: RiskLevel = RiskLevel.LOW,
        result: Optional[str] = None,
        tokens_used: Optional[int] = None,
        cost_cny: Optional[float] = None,
        execution_ms: Optional[int] = None,
        ip_address: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ):
        self.id = id
        self.user_id = user_id
        self.tool = tool
        self.params = params or {}
        self.risk_level = risk_level
        self.result = result
        self.tokens_used = tokens_used
        self.cost_cny = cost_cny
        self.execution_ms = execution_ms
        self.ip_address = ip_address
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "tool": self.tool,
            "params": self.params,
            "risk_level": self.risk_level.value,
            "result": self.result,
            "tokens_used": self.tokens_used,
            "cost_cny": self.cost_cny,
            "execution_ms": self.execution_ms,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    async def create(
        cls,
        user_id: str,
        tool: str,
        params: Dict[str, Any],
        risk_level: RiskLevel,
        execution_ms: int = 0,
        result: Optional[str] = None,
        tokens_used: Optional[int] = None,
        cost_cny: Optional[float] = None,
        ip_address: Optional[str] = None,
    ) -> "AuditLog":
        """Create and persist audit log entry using SQLAlchemy ORM.

        Args:
            user_id: User who executed the tool
            tool: Tool name that was executed
            params: Parameters passed to the tool
            risk_level: Risk level of the tool execution
            execution_ms: Execution time in milliseconds
            result: Result summary from the tool execution
            tokens_used: Number of tokens consumed
            cost_cny: Cost in CNY
            ip_address: IP address of the requester

        Returns:
            AuditLog instance with persisted data
        """
        log_id = str(uuid.uuid4())
        created_at = datetime.utcnow()

        async with AsyncSessionLocal() as session:
            try:
                orm_entry = AuditLogORM(
                    id=log_id,
                    user_id=user_id,
                    tool=tool,
                    risk_level=risk_level.value,
                    params=params,
                    result=result,
                    tokens_used=tokens_used,
                    cost_cny=cost_cny,
                    execution_ms=execution_ms,
                    ip_address=ip_address,
                    created_at=created_at,
                )
                session.add(orm_entry)
                await session.commit()

                logger.info(
                    "Audit log created",
                    log_id=log_id,
                    tool=tool,
                    risk_level=risk_level.value,
                    user_id=user_id,
                )

                return cls(
                    id=log_id,
                    user_id=user_id,
                    tool=tool,
                    params=params,
                    risk_level=risk_level,
                    result=result,
                    tokens_used=tokens_used,
                    cost_cny=cost_cny,
                    execution_ms=execution_ms,
                    ip_address=ip_address,
                    created_at=created_at,
                )
            except Exception as e:
                await session.rollback()
                logger.error("Failed to create audit log", error=str(e), tool=tool)
                # Return instance without persisted id
                return cls(
                    user_id=user_id,
                    tool=tool,
                    params=params,
                    risk_level=risk_level,
                    result=result,
                    tokens_used=tokens_used,
                    cost_cny=cost_cny,
                    execution_ms=execution_ms,
                    ip_address=ip_address,
                    created_at=created_at,
                )

    @classmethod
    async def cleanup_old_logs(
        cls, retention_days: int = AUDIT_LOG_RETENTION_DAYS
    ) -> int:
        """Delete audit logs older than retention period using SQLAlchemy ORM.

        Args:
            retention_days: Number of days to retain logs (default: 30)

        Returns:
            Number of deleted records
        """
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        async with AsyncSessionLocal() as session:
            try:
                # Count logs to be deleted
                count_stmt = select(AuditLogORM).where(
                    AuditLogORM.created_at < cutoff_date
                )
                result = await session.execute(count_stmt)
                logs_to_delete = result.scalars().all()
                count = len(logs_to_delete)

                if count > 0:
                    # Delete old logs
                    delete_stmt = delete(AuditLogORM).where(
                        AuditLogORM.created_at < cutoff_date
                    )
                    await session.execute(delete_stmt)
                    await session.commit()
                    logger.info("Audit logs cleaned up", deleted_count=count)

                return count
            except Exception as e:
                await session.rollback()
                logger.error("Failed to cleanup audit logs", error=str(e))
                return 0

    @classmethod
    async def get_user_logs(
        cls,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list["AuditLog"]:
        """Get audit logs for a specific user.

        Args:
            user_id: User ID to filter by
            limit: Maximum number of logs to return
            offset: Offset for pagination

        Returns:
            List of AuditLog instances
        """
        async with AsyncSessionLocal() as session:
            try:
                stmt = (
                    select(AuditLogORM)
                    .where(AuditLogORM.user_id == user_id)
                    .order_by(AuditLogORM.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
                result = await session.execute(stmt)
                orm_logs = result.scalars().all()

                return [
                    cls(
                        id=log.id,
                        user_id=log.user_id,
                        tool=log.tool,
                        params=log.params,
                        risk_level=RiskLevel(log.risk_level),
                        result=log.result,
                        tokens_used=log.tokens_used,
                        cost_cny=log.cost_cny,
                        execution_ms=log.execution_ms,
                        ip_address=log.ip_address,
                        created_at=log.created_at,
                    )
                    for log in orm_logs
                ]
            except Exception as e:
                logger.error("Failed to get user audit logs", error=str(e))
                return []


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
    """Get risk level for a tool name."""
    return TOOL_RISK_MAPPING.get(tool_name, RiskLevel.MEDIUM)


def requires_confirmation(tool_name: str) -> bool:
    """Check if a tool requires user confirmation before execution."""
    return get_tool_risk_level(tool_name) == RiskLevel.CRITICAL


__all__ = [
    "AuditLog",
    "RiskLevel",
    "AUDIT_LOG_RETENTION_DAYS",
    "TOOL_RISK_MAPPING",
    "get_tool_risk_level",
    "requires_confirmation",
]