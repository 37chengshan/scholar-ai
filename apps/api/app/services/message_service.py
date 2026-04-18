"""Message service for chat message persistence.

Per D-07: Service layer for message operations, separating business logic from API routes.

Responsibilities:
- Message CRUD operations (create, retrieve, delete)
- Message history retrieval with pagination
- Tool call persistence
- Session statistics update
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
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
    ) -> str:
        """Save chat message to PostgreSQL and update session stats.

        Args:
            session_id: Session UUID
            role: Message role (user, assistant, tool, system)
            content: Message content
            tool_name: Tool name if role=tool
            tool_params: Tool parameters if role=tool

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
                )
                db.add(message)

                is_tool_call = role == "tool"
                await db.execute(
                    update(Session)
                    .where(Session.id == session_id)
                    .values(
                        message_count=Session.message_count + 1,
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
        session_context = db if db else AsyncSessionLocal()

        async with session_context if not db else session_context:
            try:
                query = (
                    select(ChatMessage)
                    .where(ChatMessage.session_id == session_id)
                )

                if order == "asc":
                    query = query.order_by(ChatMessage.created_at.asc())
                else:
                    query = query.order_by(ChatMessage.created_at.desc())

                query = query.limit(limit).offset(offset)

                if db:
                    result = await db.execute(
                        query
                    )
                else:
                    async with AsyncSessionLocal() as session:
                        result = await session.execute(
                            query
                        )

                messages = result.scalars().all()

                return [
                    {
                        "id": msg.id,
                        "session_id": msg.session_id,
                        "role": msg.role,
                        "content": msg.content,
                        "tool_name": msg.tool_name,
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
        content: str,
        db: Optional[AsyncSession] = None,
    ) -> bool:
        """Update an existing message content.

        Returns True when a row is updated, otherwise False.
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if db:
            result = await db.execute(
                update(ChatMessage)
                .where(ChatMessage.id == message_id)
                .values(content=content)
            )
            return (result.rowcount or 0) > 0

        async with AsyncSessionLocal() as session:
            try:
                # Keep session activity in sync with final assistant output.
                session_result = await session.execute(
                    select(ChatMessage.session_id).where(ChatMessage.id == message_id)
                )
                session_id = session_result.scalar_one_or_none()

                result = await session.execute(
                    update(ChatMessage)
                    .where(ChatMessage.id == message_id)
                    .values(content=content)
                )

                if (result.rowcount or 0) > 0 and session_id:
                    await session.execute(
                        update(Session)
                        .where(Session.id == session_id)
                        .values(last_activity_at=now)
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
