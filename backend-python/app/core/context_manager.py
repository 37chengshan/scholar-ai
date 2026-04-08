"""Context Manager for Agent conversations.

Implements D-09 from Agent-Native architecture:
Hierarchical context storage with compression for long conversations.

Implements D-11, D-12 from Phase 25:
- Sliding window (last 20 messages)
- Vector retrieval for relevant memories
- User preferences integration

Context Structure:
- Important messages: User/system/decision points - always preserved
- Secondary messages: Tool results/intermediate steps - compressed if needed
- Recent messages: Last 20 messages (sliding window)
- Relevant memories: Top-5 from vector search
- User preferences: Language, theme, model preference
- Tool history: Recent tool executions
- Environment: Current state (user_id, paper_ids, etc.)
- Working memory: Temporary data for current execution

Usage:
    manager = ContextManager()
    context = await manager.build_context(session_id, user_id)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json

from app.core.config import settings
from app.utils.logger import logger
from app.utils.zhipu_client import get_llm_client


@dataclass
class Message:
    """Message in conversation.

    Attributes:
        role: Message role (user/assistant/tool/system)
        content: Message text
        metadata: Optional metadata (intent, citations, etc.)
        is_important: Whether this message is critical to preserve
    """

    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    is_important: bool = False


@dataclass
class Context:
    """Agent execution context.

    Attributes:
        objective: User's goal
        important_messages: Critical messages (always preserved)
        secondary_messages: Less important messages (may be compressed)
        recent_messages: Last 20 messages (sliding window)
        relevant_memories: Top-5 relevant memories from vector search
        user_preferences: User preferences (language, theme, model)
        tool_history: Recent tool executions
        environment: Current state (user_id, session_id, etc.)
        working_memory: Temporary data for current execution
    """

    objective: str = ""
    important_messages: List[Message] = field(default_factory=list)
    secondary_messages: List[Message] = field(default_factory=list)
    recent_messages: List[Message] = field(default_factory=list)
    relevant_memories: List[Any] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    tool_history: List[Dict[str, Any]] = field(default_factory=list)
    environment: Dict[str, Any] = field(default_factory=dict)
    working_memory: Dict[str, Any] = field(default_factory=dict)


class ContextManager:
    """Manages Agent conversation context with compression.

    Implements hierarchical storage:
    - Important messages: Preserved in full
    - Secondary messages: Compressed if approaching token limit
    - Recent messages: Sliding window (last 20)
    - Relevant memories: Vector retrieval for context enrichment
    """

    MAX_CONTEXT_TOKENS = 8000
    MAX_MESSAGES = 20  # Per D-11
    COMPRESSION_THRESHOLD = 5  # Compress if > 5 secondary messages

    def __init__(self):
        """Initialize ContextManager with MemorySearch."""
        self.memory_search = None

    def is_important_message(self, message: Message) -> bool:
        """Check if message is important.

        Important messages are:
        - User messages
        - System messages
        - Messages with decision points
        - Messages with citations

        Args:
            message: Message to check

        Returns:
            True if message is important
        """
        if message.role == "user" or message.role == "system":
            return True

        if message.metadata:
            if message.metadata.get("is_decision_point", False):
                return True
            if message.metadata.get("has_citations", False):
                return True

        return False

    async def build_context(
        self, session_id: str, user_id: Optional[str] = None
    ) -> Context:
        """Build context from session.

        Per D-11, D-12:
        1. Fetch session and messages from DB
        2. Apply sliding window (last 20 messages)
        3. Separate important vs secondary messages
        4. Retrieve relevant memories via vector search
        5. Fetch user preferences
        6. Compress if approaching token limit

        Args:
            session_id: Session ID
            user_id: User ID (for memory retrieval)

        Returns:
            Context object
        """
        from app.core.database import get_db_connection

        logger.info("Building context", session_id=session_id, user_id=user_id)

        # Fetch messages from database
        messages = []
        try:
            async with get_db_connection() as conn:
                rows = await conn.fetch(
                    """
                    SELECT role, content, metadata
                    FROM chat_messages
                    WHERE session_id = $1
                    ORDER BY created_at ASC
                    """,
                    session_id,
                )

                messages = [
                    Message(
                        role=row["role"],
                        content=row["content"],
                        metadata=json.loads(row["metadata"])
                        if row["metadata"]
                        else None,
                    )
                    for row in rows
                ]
        except Exception as e:
            logger.error(
                "Failed to fetch messages", error=str(e), session_id=session_id
            )
            # Return empty context on error
            return Context(environment={"session_id": session_id, "user_id": user_id})

        # Apply sliding window - Per D-11
        recent_messages = (
            messages[-self.MAX_MESSAGES :]
            if len(messages) > self.MAX_MESSAGES
            else messages
        )

        # Separate important and secondary messages
        important = []
        secondary = []

        for msg in messages:
            if self.is_important_message(msg):
                msg.is_important = True
                important.append(msg)
            else:
                secondary.append(msg)

        # Retrieve relevant memories via vector search - Per D-11, D-12
        relevant_memories = []
        user_preferences = {}

        if user_id and len(messages) > 0:
            try:
                if not self.memory_search:
                    from app.core.memory_search import MemorySearch

                    self.memory_search = MemorySearch()

                # Get objective from last user message
                objective = None
                for msg in reversed(messages):
                    if msg.role == "user":
                        objective = msg.content
                        break

                if objective:
                    relevant_memories = await self.memory_search.search_memories(
                        query=objective,
                        user_id=user_id,
                        top_k=5,
                    )

                    logger.info(
                        "Retrieved relevant memories",
                        user_id=user_id,
                        count=len(relevant_memories),
                    )

                # Get user preferences - Per D-12
                user_preferences = await self.get_user_preferences(user_id)

            except Exception as e:
                logger.error(
                    "Failed to retrieve memories", error=str(e), user_id=user_id
                )
                # Continue without memories on error

        # Check token limit
        current_tokens = self.count_tokens(important)

        # Compress if approaching limit
        if current_tokens > self.MAX_CONTEXT_TOKENS * 0.7 and len(secondary) > 0:
            logger.info(
                "Compressing secondary messages",
                current_tokens=current_tokens,
                secondary_count=len(secondary),
            )
            secondary = await self.compress_secondary_messages(secondary)

        return Context(
            objective=objective if "objective" in locals() else "",
            important_messages=important,
            secondary_messages=secondary,
            recent_messages=recent_messages,
            relevant_memories=relevant_memories,
            user_preferences=user_preferences,
            environment={"session_id": session_id, "user_id": user_id},
        )

    async def compress_secondary_messages(
        self, messages: List[Message]
    ) -> List[Message]:
        """Compress secondary messages into summary.

        Uses GLM-4.5-Air to generate summary if > threshold messages.

        Args:
            messages: Messages to compress

        Returns:
            List with single summary message if compressed, else original
        """
        if len(messages) <= self.COMPRESSION_THRESHOLD:
            return messages

        # Format messages for LLM
        message_texts = [f"{msg.role}: {msg.content}" for msg in messages]

        combined_text = "\n".join(message_texts)

        try:
            llm_client = get_llm_client()

            # Use GLM-4.5-Air to summarize
            response = await llm_client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "Summarize these tool execution results, preserving key information. Be concise.",
                    },
                    {"role": "user", "content": combined_text},
                ],
                max_tokens=500,
            )

            summary = response.choices[0].message.content

            logger.info(
                "Compressed messages",
                original_count=len(messages),
                summary_length=len(summary),
            )

            # Return summary as system message
            return [
                Message(
                    role="system",
                    content=f"[历史执行摘要] {summary}",
                    is_important=False,
                )
            ]

        except Exception as e:
            logger.error("Failed to compress messages", error=str(e))
            # Return original messages if compression fails
            return messages

    def count_tokens(self, messages: List[Message]) -> int:
        """Estimate token count for messages.

        Simple estimation: 1 token ≈ 4 characters.

        Args:
            messages: Messages to count

        Returns:
            Estimated token count
        """
        total_chars = sum(len(msg.content) for msg in messages)
        return total_chars // 4

    async def save_context(self, session_id: str, context: Context) -> None:
        """Save context to Redis.

        Args:
            session_id: Session ID
            context: Context to save
        """
        from app.utils.cache import save_conversation_session

        try:
            # Save via cache module
            context_data = {
                "objective": context.objective,
                "important_count": len(context.important_messages),
                "secondary_count": len(context.secondary_messages),
                "tool_history": context.tool_history,
            }

            await save_conversation_session(session_id, context_data)

            logger.info("Saved context", session_id=session_id)

        except Exception as e:
            logger.error("Failed to save context", error=str(e), session_id=session_id)

    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences from database.

        Per D-12: Fetch user preferences (language, theme, model) from User.settings.

        Args:
            user_id: User ID

        Returns:
            Dict of user preferences
        """
        from app.core.database import get_db_connection

        try:
            async with get_db_connection() as conn:
                # Fetch from users table (Node.js backend manages this)
                # For now, return empty dict
                # In production, this would query the users table
                return {}

        except Exception as e:
            logger.error("Failed to get user preferences", error=str(e), user_id=user_id)
            return {}
