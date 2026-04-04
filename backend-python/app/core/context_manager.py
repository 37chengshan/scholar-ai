"""Context Manager for Agent conversations.

Implements D-09 from Agent-Native architecture:
Hierarchical context storage with compression for long conversations.

Context Structure:
- Important messages: User/system/decision points - always preserved
- Secondary messages: Tool results/intermediate steps - compressed if needed
- Tool history: Recent tool executions
- Environment: Current state (user_id, paper_ids, etc.)
- Working memory: Temporary data for current execution

Usage:
    manager = ContextManager()
    context = await manager.build_context(session_id)
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
        tool_history: Recent tool executions
        environment: Current state (user_id, session_id, etc.)
        working_memory: Temporary data for current execution
    """
    
    objective: str = ""
    important_messages: List[Message] = field(default_factory=list)
    secondary_messages: List[Message] = field(default_factory=list)
    tool_history: List[Dict[str, Any]] = field(default_factory=list)
    environment: Dict[str, Any] = field(default_factory=dict)
    working_memory: Dict[str, Any] = field(default_factory=dict)


class ContextManager:
    """Manages Agent conversation context with compression.
    
    Implements hierarchical storage:
    - Important messages: Preserved in full
    - Secondary messages: Compressed if approaching token limit
    - Tool history: Last N executions
    """
    
    MAX_CONTEXT_TOKENS = 8000
    COMPRESSION_THRESHOLD = 5  # Compress if > 5 secondary messages
    
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
    
    async def build_context(self, session_id: str) -> Context:
        """Build context from session.
        
        1. Fetch session and messages from DB
        2. Separate important vs secondary messages
        3. Compress if approaching token limit
        
        Args:
            session_id: Session ID
            
        Returns:
            Context object
        """
        from app.core.database import get_db_connection
        
        logger.info("Building context", session_id=session_id)
        
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
                    session_id
                )
                
                messages = [
                    Message(
                        role=row["role"],
                        content=row["content"],
                        metadata=json.loads(row["metadata"]) if row["metadata"] else None
                    )
                    for row in rows
                ]
        except Exception as e:
            logger.error("Failed to fetch messages", error=str(e), session_id=session_id)
            # Return empty context on error
            return Context(environment={"session_id": session_id})
        
        # Separate important and secondary messages
        important = []
        secondary = []
        
        for msg in messages:
            if self.is_important_message(msg):
                msg.is_important = True
                important.append(msg)
            else:
                secondary.append(msg)
        
        # Check token limit
        current_tokens = self.count_tokens(important)
        
        # Compress if approaching limit
        if current_tokens > self.MAX_CONTEXT_TOKENS * 0.7 and len(secondary) > 0:
            logger.info(
                "Compressing secondary messages",
                current_tokens=current_tokens,
                secondary_count=len(secondary)
            )
            secondary = await self.compress_secondary_messages(secondary)
        
        return Context(
            important_messages=important,
            secondary_messages=secondary,
            environment={"session_id": session_id}
        )
    
    async def compress_secondary_messages(
        self,
        messages: List[Message]
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
        message_texts = [
            f"{msg.role}: {msg.content}"
            for msg in messages
        ]
        
        combined_text = "\n".join(message_texts)
        
        try:
            llm_client = get_llm_client()
            
            # Use GLM-4.5-Air to summarize
            response = await llm_client.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "Summarize these tool execution results, preserving key information. Be concise."
                    },
                    {
                        "role": "user",
                        "content": combined_text
                    }
                ],
                max_tokens=500
            )
            
            summary = response.choices[0].message.content
            
            logger.info(
                "Compressed messages",
                original_count=len(messages),
                summary_length=len(summary)
            )
            
            # Return summary as system message
            return [
                Message(
                    role="system",
                    content=f"[历史执行摘要] {summary}",
                    is_important=False
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
    
    async def save_context(
        self,
        session_id: str,
        context: Context
    ) -> None:
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
                "tool_history": context.tool_history
            }
            
            await save_conversation_session(session_id, context_data)
            
            logger.info("Saved context", session_id=session_id)
            
        except Exception as e:
            logger.error("Failed to save context", error=str(e), session_id=session_id)