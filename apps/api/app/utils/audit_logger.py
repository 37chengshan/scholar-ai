"""Audit Logger service for tool execution tracking.

Implements D-08, D-09 from Agent-Native architecture:
- Record all tool executions with performance metrics
- Track token usage, cost, and execution time
- Retain logs for 30 days
- Query logs by user, date range, and risk level

Usage:
    logger = AuditLogger()
    await logger.record(
        user_id="user123",
        tool="delete_paper",
        risk_level="CRITICAL",
        params={"paper_id": "paper456"},
        tokens_used=150,
        cost_cny=0.003,
        execution_ms=250
    )
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta

from sqlalchemy import delete, func, select

from app.database import AsyncSessionLocal
from app.models.orm_audit_log import AuditLog
from app.utils.logger import logger


class AuditLogger:
    """Audit logging service for tool execution tracking.

    Provides comprehensive audit trail for all tool executions:
    - Record tool calls with parameters and results
    - Track performance metrics (tokens, cost, execution time)
    - Query logs by user and date range
    - Generate risk summary statistics
    - Cleanup old logs per retention policy

    Attributes:
        DEFAULT_RETENTION_DAYS: Default log retention period (30 days per D-09)
    """

    DEFAULT_RETENTION_DAYS = 30  # Per D-09

    async def record(
        self,
        user_id: str,
        tool: str,
        risk_level: str,
        params: Optional[Dict[str, Any]] = None,
        result: Optional[str] = None,
        tokens_used: Optional[int] = None,
        cost_cny: Optional[float] = None,
        execution_ms: Optional[int] = None,
        ip_address: Optional[str] = None,
    ) -> bool:
        """Record a tool execution to audit log.

        Args:
            user_id: User who executed the tool
            tool: Tool name (e.g., 'delete_paper', 'rag_search')
            risk_level: Risk level (LOW, MEDIUM, HIGH, CRITICAL)
            params: Tool parameters
            result: Tool result summary
            tokens_used: Tokens consumed
            cost_cny: Cost in CNY
            execution_ms: Execution time in milliseconds
            ip_address: Client IP address

        Returns:
            True if logged successfully, False otherwise
        """
        try:
            created_at = datetime.now(timezone.utc)

            async with AsyncSessionLocal() as db:
                # Create AuditLog ORM object
                log_entry = AuditLog(
                    user_id=user_id,
                    tool=tool,
                    risk_level=risk_level,
                    params=params,
                    result=result,
                    tokens_used=tokens_used,
                    cost_cny=cost_cny,
                    execution_ms=execution_ms,
                    ip_address=ip_address,
                    created_at=created_at,
                )
                db.add(log_entry)
                await db.flush()  # Flush to get the ID without committing

                log_id = log_entry.id

            logger.info(
                "Audit log recorded",
                log_id=log_id,
                user_id=user_id,
                tool=tool,
                risk_level=risk_level,
                tokens_used=tokens_used,
                cost_cny=cost_cny,
                execution_ms=execution_ms,
            )

            return True

        except Exception as e:
            # Log error but don't raise - audit logging failure should not block execution
            logger.error(
                "Failed to record audit log",
                error=str(e),
                user_id=user_id,
                tool=tool,
            )
            return False

    async def get_user_audit(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get audit logs for a user within date range.

        Args:
            user_id: User ID to query
            start_date: Start of date range
            end_date: End of date range
            limit: Maximum number of logs to return
            offset: Offset for pagination

        Returns:
            List of audit log records
        """
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(AuditLog)
                    .where(AuditLog.user_id == user_id)
                    .where(AuditLog.created_at >= start_date)
                    .where(AuditLog.created_at <= end_date)
                    .order_by(AuditLog.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
                logs = result.scalars().all()

                # Convert ORM objects to dicts
                return [
                    {
                        "id": log.id,
                        "user_id": log.user_id,
                        "tool": log.tool,
                        "risk_level": log.risk_level,
                        "params": log.params,
                        "result": log.result,
                        "tokens_used": log.tokens_used,
                        "cost_cny": log.cost_cny,
                        "execution_ms": log.execution_ms,
                        "ip_address": log.ip_address,
                        "created_at": log.created_at,
                    }
                    for log in logs
                ]

        except Exception as e:
            logger.error(
                "Failed to get user audit logs",
                error=str(e),
                user_id=user_id,
            )
            return []

    async def get_risk_summary(self, user_id: str, days: int = 7) -> Dict[str, int]:
        """Get risk level summary for user.

        Args:
            user_id: User ID to query
            days: Number of days to look back

        Returns:
            Dict with count per risk level (LOW, MEDIUM, HIGH, CRITICAL)
        """
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)

            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(AuditLog.risk_level, func.count(AuditLog.id).label("count"))
                    .where(AuditLog.user_id == user_id)
                    .where(AuditLog.created_at >= start_date)
                    .group_by(AuditLog.risk_level)
                )
                rows = result.all()

                # Initialize with all risk levels
                summary = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}

                # Update with actual counts
                for row in rows:
                    level = row.risk_level
                    if level in summary:
                        summary[level] = row.count

                return summary

        except Exception as e:
            logger.error(
                "Failed to get risk summary",
                error=str(e),
                user_id=user_id,
            )
            return {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}

    async def cleanup_old_logs(self, days: Optional[int] = None) -> int:
        """Delete audit logs older than specified days.

        Per D-09: Default retention is 30 days.

        Args:
            days: Number of days to retain (default: 30)

        Returns:
            Number of deleted records
        """
        retention_days = days or self.DEFAULT_RETENTION_DAYS

        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

            async with AsyncSessionLocal() as db:
                # First count how many will be deleted
                count_result = await db.execute(
                    select(func.count(AuditLog.id)).where(AuditLog.created_at < cutoff_date)
                )
                deleted_count = count_result.scalar() or 0

                # Delete old logs
                if deleted_count > 0:
                    await db.execute(delete(AuditLog).where(AuditLog.created_at < cutoff_date))

                logger.info(
                    "Audit logs cleaned up",
                    deleted_count=deleted_count,
                    cutoff_date=cutoff_date.isoformat(),
                    retention_days=retention_days,
                )

                return deleted_count

        except Exception as e:
            logger.error(
                "Failed to cleanup old audit logs",
                error=str(e),
                retention_days=retention_days,
            )
            return 0


# Singleton instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create AuditLogger singleton instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger