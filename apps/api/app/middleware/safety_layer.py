"""Safety Layer middleware for tool execution.

Per D-07: Assesses risk and blocks CRITICAL tools without confirmation.
Per D-08: Logs all tool calls with performance metrics.
Per D-09: Implements 30-day audit log retention.

Safety Layer intercepts tool execution and:
1. Assesses risk level before allowing execution
2. Blocks CRITICAL tools until user confirms
3. Logs all tool executions to audit trail
4. Tracks execution time and token usage
"""

from datetime import datetime
from typing import Any, Dict, Optional
import time

from app.models.audit_log import (
    AuditLog,
    RiskLevel,
    get_tool_risk_level,
    requires_confirmation,
)
from app.utils.logger import logger


class SafetyLayer:
    """Safety Layer for tool execution governance.

    Intercepts tool calls to:
    - Assess risk level (LOW/MEDIUM/HIGH/CRITICAL)
    - Block CRITICAL tools without user confirmation
    - Log all executions to audit trail
    - Track performance metrics (time, tokens)

    Attributes:
        audit_log_enabled: Whether audit logging is enabled
        auto_confirm: Auto-confirm mode (for testing)
    """

    def __init__(self, audit_log_enabled: bool = True, auto_confirm: bool = False):
        """Initialize Safety Layer.

        Args:
            audit_log_enabled: Enable audit logging (default: True)
            auto_confirm: Auto-confirm for testing (default: False)
        """
        self.audit_log_enabled = audit_log_enabled
        self.auto_confirm = auto_confirm

    async def assess_risk(
        self,
        tool_name: str,
        params: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Assess risk level for tool execution.

        Per D-07: CRITICAL tools (delete_paper, execute_command) require confirmation.
        LOW/MEDIUM/HIGH risks log but don't block.

        Args:
            tool_name: Tool to assess
            params: Tool parameters
            context: Execution context (user_id, session_id, etc.)

        Returns:
            Dict with:
                - risk_level: LOW|MEDIUM|HIGH|CRITICAL
                - requires_confirmation: Whether user confirmation needed
                - message: Risk assessment message
        """
        # Get risk level from mapping
        risk_level = get_tool_risk_level(tool_name)

        # Determine if confirmation needed
        needs_confirmation = requires_confirmation(tool_name)

        # Build risk message
        message = self._build_risk_message(tool_name, risk_level, params)

        logger.info(
            "Risk assessed",
            tool=tool_name,
            risk_level=risk_level.value,
            requires_confirmation=needs_confirmation,
        )

        return {
            "risk_level": risk_level.value,
            "requires_confirmation": needs_confirmation,
            "message": message,
        }

    def _build_risk_message(
        self,
        tool_name: str,
        risk_level: RiskLevel,
        params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build risk assessment message.

        Args:
            tool_name: Tool name
            risk_level: Risk level
            params: Tool parameters

        Returns:
            Human-readable risk message
        """
        params = params or {}

        if risk_level == RiskLevel.CRITICAL:
            # Specific messages for CRITICAL tools
            if tool_name == "delete_paper":
                paper_title = params.get("title", "this paper")
                return f"Delete '{paper_title}': This action cannot be undone."

            elif tool_name == "execute_command":
                command = params.get("command", "unknown command")
                return f"Run command: '{command}' may modify files or system."

            return f"CRITICAL operation: {tool_name} requires confirmation."

        elif risk_level == RiskLevel.HIGH:
            return f"HIGH risk: {tool_name} will modify data."

        elif risk_level == RiskLevel.MEDIUM:
            return f"MEDIUM risk: {tool_name} will create or update content."

        else:  # LOW
            return f"LOW risk: {tool_name} is read-only."

    async def check_permission(
        self,
        tool_name: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Check permission for tool execution.

        Wrapper around assess_risk for backward compatibility.

        Args:
            tool_name: Tool name
            context: Permission context

        Returns:
            Permission result dict
        """
        return await self.assess_risk(tool_name, context.get("parameters"), context)

    async def log_audit(
        self,
        user_id: str,
        session_id: str,
        tool_name: str,
        params: Dict[str, Any],
        execution_time_ms: int,
        token_usage: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        confirmed: bool = False,
    ) -> Optional[AuditLog]:
        """Log tool execution to audit trail.

        Per D-08: Records tool_name, risk_level, execution_time_ms, token_usage.

        Args:
            user_id: User ID
            session_id: Session ID
            tool_name: Tool name
            params: Tool parameters
            execution_time_ms: Execution time in milliseconds
            token_usage: Token usage data
            result: Tool execution result
            confirmed: Whether user confirmed (for CRITICAL tools)

        Returns:
            Created AuditLog entry or None if logging failed
        """
        if not self.audit_log_enabled:
            return None

        # Get risk level
        risk_level = get_tool_risk_level(tool_name)

        # Build result summary
        result_summary = ""
        if result:
            if result.get("success"):
                result_summary = "Success"
            else:
                result_summary = f"Failed: {result.get('error', 'Unknown error')}"

        # Create audit log
        try:
            audit_log = await AuditLog.create(
                user_id=user_id,
                session_id=session_id,
                tool_name=tool_name,
                params=params,
                risk_level=risk_level,
                execution_time_ms=execution_time_ms,
                token_usage=token_usage,
                confirmed=confirmed,
                result_summary=result_summary,
            )

            return audit_log

        except Exception as e:
            logger.error("Failed to log audit", error=str(e))
            return None

    async def cleanup_audit_logs(
        self,
        retention_days: int = 30,
    ) -> int:
        """Clean up old audit logs.

        Per D-09: 30-day retention with automatic cleanup.

        Args:
            retention_days: Days to retain (default: 30)

        Returns:
            Number of deleted logs
        """
        try:
            deleted_count = await AuditLog.cleanup_old_logs(retention_days)

            logger.info(
                "Audit log cleanup completed",
                deleted_count=deleted_count,
                retention_days=retention_days,
            )

            return deleted_count

        except Exception as e:
            logger.error("Audit log cleanup failed", error=str(e))
            return 0


class SafetyLayerContext:
    """Context manager for timing tool execution.

    Usage:
        async with SafetyLayerContext(safety_layer, user_id, session_id, tool_name, params) as ctx:
            result = await execute_tool()
            # Timing and logging handled automatically
    """

    def __init__(
        self,
        safety_layer: SafetyLayer,
        user_id: str,
        session_id: str,
        tool_name: str,
        params: Dict[str, Any],
    ):
        """Initialize context.

        Args:
            safety_layer: SafetyLayer instance
            user_id: User ID
            session_id: Session ID
            tool_name: Tool name
            params: Tool parameters
        """
        self.safety_layer = safety_layer
        self.user_id = user_id
        self.session_id = session_id
        self.tool_name = tool_name
        self.params = params
        self.start_time: Optional[float] = None
        self.result: Optional[Dict[str, Any]] = None
        self.audit_log: Optional[AuditLog] = None

    async def __aenter__(self) -> "SafetyLayerContext":
        """Enter context - assess risk."""
        # Assess risk before execution
        risk_result = await self.safety_layer.assess_risk(
            self.tool_name,
            self.params,
        )

        # Check if confirmation needed
        if risk_result.get("requires_confirmation"):
            raise PermissionError(f"Tool '{self.tool_name}' requires user confirmation")

        # Start timing
        self.start_time = time.time()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit context - log audit."""
        if self.start_time:
            execution_time_ms = int((time.time() - self.start_time) * 1000)

            # Build result
            if exc_type:
                self.result = {
                    "success": False,
                    "error": str(exc_val),
                }
            elif self.result is None:
                self.result = {"success": True}

            # Log audit
            self.audit_log = await self.safety_layer.log_audit(
                user_id=self.user_id,
                session_id=self.session_id,
                tool_name=self.tool_name,
                params=self.params,
                execution_time_ms=execution_time_ms,
                result=self.result,
            )

        # Don't suppress exceptions
        return False


__all__ = [
    "SafetyLayer",
    "SafetyLayerContext",
]
