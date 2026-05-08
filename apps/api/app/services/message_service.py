"""Message service for chat message persistence.

Per D-07: Service layer for message operations, separating business logic from API routes.

Responsibilities:
- Message CRUD operations (create, retrieve, delete)
- Message history retrieval with pagination
- Tool call persistence
- Session statistics update
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select, delete, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import ChatMessage, Session
from app.utils.logger import logger


class MessageService:
    """Service for chat message persistence and retrieval."""

    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_name: Optional[str] = None,
        tool_params: Optional[Dict] = None,
        reasoning_content: Optional[str] = None,
        current_phase: Optional[str] = None,
        tool_timeline: Optional[List[Dict[str, Any]]] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
        answer_contract: Optional[Dict[str, Any]] = None,
        stream_status: Optional[str] = None,
        tokens_used: Optional[int] = None,
        cost: Optional[float] = None,
        duration_ms: Optional[int] = None,
        response_type: Optional[str] = None,
        trace_id: Optional[str] = None,
        run_id: Optional[str] = None,
        count_towards_stats: bool = True,
    ) -> str:
        """Save chat message to PostgreSQL and update session stats.

        Args:
            session_id: Session UUID
            role: Message role (user, assistant, tool, system)
            content: Message content
            tool_name: Tool name if role=tool
            tool_params: Tool parameters if role=tool
            count_towards_stats: Whether to increment session.message_count

        Returns:
            Message UUID

        Raises:
            Exception: If database insert fails
        """
        message_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).replace(tzinfo=None)

        async with AsyncSessionLocal() as db:
            try:
                message = ChatMessage(
                    id=message_id,
                    session_id=session_id,
                    role=role,
                    content=content,
                    tool_name=tool_name,
                    tool_params=tool_params,
                    reasoning_content=reasoning_content,
                    current_phase=current_phase,
                    tool_timeline=tool_timeline,
                    citations=citations,
                    answer_contract=answer_contract,
                    stream_status=stream_status,
                    tokens_used=tokens_used,
                    cost=cost,
                    duration_ms=duration_ms,
                    response_type=response_type,
                    trace_id=trace_id,
                    run_id=run_id,
                )
                db.add(message)

                is_tool_call = role == "tool"
                message_count_delta = 1 if count_towards_stats else 0
                await db.execute(
                    update(Session)
                    .where(Session.id == session_id)
                    .values(
                        message_count=Session.message_count + message_count_delta,
                        tool_call_count=Session.tool_call_count
                        + (1 if is_tool_call else 0),
                        last_activity_at=created_at,
                    )
                )

                await db.commit()

                logger.debug(
                    "Message saved",
                    message_id=message_id,
                    session_id=session_id,
                    role=role,
                )

                return message_id
            except Exception:
                await db.rollback()
                raise

    async def get_messages(
        self,
        session_id: str,
        limit: int = 50,
        offset: int = 0,
        order: str = "desc",
        db: Optional[AsyncSession] = None,
    ) -> List[Dict]:
        """Retrieve messages for a session with pagination.

        Args:
            session_id: Session UUID
            limit: Maximum number of messages (default 50)
            offset: Offset for pagination (default 0)
            order: Sort order by created_at (asc|desc, default desc)
            db: Optional database session (for transaction continuity)

        Returns:
            List of message dictionaries
        """
        try:
            query = select(ChatMessage).where(ChatMessage.session_id == session_id)

            if order == "asc":
                query = query.order_by(ChatMessage.created_at.asc())
            else:
                query = query.order_by(ChatMessage.created_at.desc())

            query = query.limit(limit).offset(offset)

            if db:
                result = await db.execute(query)
            else:
                async with AsyncSessionLocal() as session:
                    result = await session.execute(query)

            messages = result.scalars().all()

            return [
                {
                    "id": msg.id,
                    "session_id": msg.session_id,
                    "role": msg.role,
                    "content": msg.content,
                    "tool_name": msg.tool_name,
                    "reasoning_content": msg.reasoning_content,
                    "current_phase": msg.current_phase,
                    "tool_timeline": msg.tool_timeline,
                    "citations": msg.citations,
                    "answer_contract": msg.answer_contract,
                    "stream_status": msg.stream_status,
                    "tokens_used": msg.tokens_used,
                    "cost": msg.cost,
                    "duration_ms": msg.duration_ms,
                    "response_type": msg.response_type,
                    "trace_id": msg.trace_id,
                    "run_id": msg.run_id,
                    "created_at": msg.created_at.isoformat()
                    if msg.created_at
                    else None,
                }
                for msg in messages
            ]
        except Exception as e:
            logger.error(
                "Failed to get messages", error=str(e), session_id=session_id
            )
            raise

    async def count_messages(
        self,
        session_id: str,
        db: Optional[AsyncSession] = None,
    ) -> int:
        """Count total messages for a session (without pagination)."""
        if db:
            result = await db.execute(
                select(func.count()).select_from(ChatMessage).where(
                    ChatMessage.session_id == session_id
                )
            )
            return int(result.scalar_one() or 0)

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(func.count()).select_from(ChatMessage).where(
                    ChatMessage.session_id == session_id
                )
            )
            return int(result.scalar_one() or 0)

    async def update_message(
        self,
        message_id: str,
        content: Optional[str] = None,
        reasoning_content: Optional[str] = None,
        current_phase: Optional[str] = None,
        tool_timeline: Optional[List[Dict[str, Any]]] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
        answer_contract: Optional[Dict[str, Any]] = None,
        stream_status: Optional[str] = None,
        tokens_used: Optional[int] = None,
        cost: Optional[float] = None,
        duration_ms: Optional[int] = None,
        response_type: Optional[str] = None,
        trace_id: Optional[str] = None,
        run_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> bool:
        """Update an existing message content.

        Returns True when a row is updated, otherwise False.
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        async def _update_session_activity(
            session: AsyncSession,
            session_id: str,
            old_role: str,
            old_content: Optional[str],
        ) -> None:
            next_content = content if content is not None else (old_content or "")
            is_placeholder_finalized = (
                old_role == "assistant"
                and (old_content or "") == ""
                and next_content != ""
            )

            values = {"last_activity_at": now}
            if is_placeholder_finalized:
                values["message_count"] = Session.message_count + 1

            await session.execute(
                update(Session)
                .where(Session.id == session_id)
                .values(**values)
            )

        update_values = {
            "content": content,
            "reasoning_content": reasoning_content,
            "current_phase": current_phase,
            "tool_timeline": tool_timeline,
            "citations": citations,
            "answer_contract": answer_contract,
            "stream_status": stream_status,
            "tokens_used": tokens_used,
            "cost": cost,
            "duration_ms": duration_ms,
            "response_type": response_type,
            "trace_id": trace_id,
            "run_id": run_id,
        }
        filtered_values = {
            key: value for key, value in update_values.items() if value is not None
        }
        if not filtered_values:
            return False

        if db:
            row = await db.execute(
                select(
                    ChatMessage.session_id,
                    ChatMessage.role,
                    ChatMessage.content,
                ).where(ChatMessage.id == message_id)
            )
            message_meta = row.first()
            result = await db.execute(
                update(ChatMessage)
                .where(ChatMessage.id == message_id)
                .values(**filtered_values)
            )
            if (result.rowcount or 0) > 0 and message_meta:
                await _update_session_activity(
                    db,
                    message_meta[0],
                    message_meta[1],
                    message_meta[2],
                )
            return (result.rowcount or 0) > 0

        async with AsyncSessionLocal() as session:
            try:
                message_result = await session.execute(
                    select(
                        ChatMessage.session_id,
                        ChatMessage.role,
                        ChatMessage.content,
                    ).where(ChatMessage.id == message_id)
                )
                message_meta = message_result.first()

                result = await session.execute(
                    update(ChatMessage)
                    .where(ChatMessage.id == message_id)
                    .values(**filtered_values)
                )

                if (result.rowcount or 0) > 0 and message_meta:
                    await _update_session_activity(
                        session,
                        message_meta[0],
                        message_meta[1],
                        message_meta[2],
                    )

                await session.commit()
                return (result.rowcount or 0) > 0
            except Exception:
                await session.rollback()
                raise

    async def delete_session_messages(self, session_id: str) -> int:
        """Delete all messages for a session.

        Args:
            session_id: Session UUID

        Returns:
            Number of messages deleted
        """
        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(
                    delete(ChatMessage).where(ChatMessage.session_id == session_id)
                )
                await db.commit()

                deleted_count = result.rowcount
                logger.info(
                    f"Deleted {deleted_count} messages for session {session_id}"
                )
                return deleted_count
            except Exception as e:
                await db.rollback()
                logger.error(
                    "Failed to delete messages", error=str(e), session_id=session_id
                )
                raise

    async def get_tool_calls(
        self,
        session_id: str,
        tool_name: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict]:
        """Retrieve tool call history for a session.

        Args:
            session_id: Session UUID
            tool_name: Optional filter by tool name
            limit: Maximum number of tool calls (default 20)

        Returns:
            List of tool call records
        """
        async with AsyncSessionLocal() as db:
            try:
                query = select(ChatMessage).where(
                    ChatMessage.session_id == session_id,
                    ChatMessage.role == "tool",
                )

                if tool_name:
                    query = query.where(ChatMessage.tool_name == tool_name)

                query = query.order_by(ChatMessage.created_at.desc()).limit(limit)

                result = await db.execute(query)
                messages = result.scalars().all()

                return [
                    {
                        "id": msg.id,
                        "tool_name": msg.tool_name,
                        "tool_params": msg.tool_params,
                        "content": msg.content,
                        "created_at": msg.created_at.isoformat()
                        if msg.created_at
                        else None,
                    }
                    for msg in messages
                ]
            except Exception as e:
                logger.error(
                    "Failed to get tool calls", error=str(e), session_id=session_id
                )
                raise


message_service = MessageService()
