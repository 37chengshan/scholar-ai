"""GLM-4.5-Air LLM client with Function Call support.

Provides unified interface for GLM-4.5-Air via zhipuai SDK:
- chat_with_tools(): Function calling with tool schemas
- chat_stream(): Streaming with reasoning_content support
- Rate limiting and exponential backoff

Usage:
    client = GLM45AirClient()
    result = await client.chat_with_tools(system_prompt, messages, tools)
    for chunk in client.chat_stream(system_prompt, messages):
        print(chunk)
"""

from typing import Any, Dict, List, Optional
from zhipuai import ZhipuAI
import json
import asyncio

from app.utils.logger import logger
from app.config import settings


class GLM45AirClient:
    """GLM-4.5-Air LLM client via zhipuai SDK.
    
    Features:
    - Function calling (tool use)
    - Streaming with reasoning_content
    - Rate limit handling with exponential backoff
    - Token usage logging
    
    Attributes:
        model: Model identifier (default: glm-4.5-air)
        max_tokens: Maximum output tokens
        temperature: Sampling temperature
        max_retries: Maximum retry attempts for rate limits
    """
    
    def __init__(
        self,
        model: str = "glm-4.5-air",
        max_tokens: int = 2048,
        temperature: float = 0.7,
        max_retries: int = 5
    ):
        """Initialize GLM-4.5-Air client.
        
        Args:
            model: Model identifier (glm-4.5-air or glm-4.5)
            max_tokens: Maximum tokens for response
            temperature: Sampling temperature (0.0-1.0)
            max_retries: Maximum retries for rate limits
        """
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_retries = max_retries
        
        # Initialize zhipuai client
        self.client = ZhipuAI(api_key=settings.ZHIPU_API_KEY)
        
        logger.info(
            "GLM-4.5-Air client initialized",
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )
    
    async def chat_with_tools(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        tool_choice: str = "auto"
    ) -> Dict[str, Any]:
        """Call GLM-4.5-Air with function calling.
        
        Args:
            system_prompt: System prompt for agent
            messages: Conversation messages
            tools: Tool schemas (OpenAI Functions format)
            tool_choice: Tool choice mode (auto, none, or specific tool)
            
        Returns:
            Dict with:
                - is_complete: Whether LLM provided final answer
                - content: (if complete) Final answer text
                - tool_call: (if not complete) Tool call dict
                - usage: Token usage statistics
        """
        logger.info(
            "Calling GLM-4.5-Air with tools",
            message_count=len(messages),
            tool_count=len(tools)
        )
        
        # Prepare messages with system prompt
        full_messages = [
            {"role": "system", "content": system_prompt},
            *messages
        ]
        
        # Retry loop for rate limits
        for attempt in range(self.max_retries):
            try:
                # Call LLM (run in thread pool for async compatibility)
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=self.model,
                    messages=full_messages,
                    tools=tools,
                    tool_choice=tool_choice,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature
                )
                
                # Parse response
                message = response.choices[0].message
                
                # Log token usage
                usage = response.usage
                logger.info(
                    "GLM-4.5-Air response",
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.total_tokens,
                    has_tool_calls=bool(message.tool_calls)
                )
                
                # Check if LLM made a tool call
                if message.tool_calls:
                    # Extract first tool call
                    tool_call = message.tool_calls[0]
                    
                    return {
                        "is_complete": False,
                        "tool_call": {
                            "name": tool_call.function.name,
                            "parameters": json.loads(tool_call.function.arguments)
                        },
                        "usage": {
                            "prompt_tokens": usage.prompt_tokens,
                            "completion_tokens": usage.completion_tokens,
                            "total_tokens": usage.total_tokens
                        }
                    }
                
                # No tool call - treat as final answer
                content = message.content
                
                return {
                    "is_complete": True,
                    "content": content,
                    "usage": {
                        "prompt_tokens": usage.prompt_tokens,
                        "completion_tokens": usage.completion_tokens,
                        "total_tokens": usage.total_tokens
                    }
                }
                
            except Exception as e:
                error_msg = str(e)
                
                # Check for rate limit errors
                if "rate" in error_msg.lower() or "limit" in error_msg.lower():
                    if attempt < self.max_retries - 1:
                        wait_time = (attempt + 1) * 1.0  # 1s, 2s, 3s, ...
                        logger.warning(
                            "Rate limit hit, retrying",
                            attempt=attempt,
                            wait_time=wait_time
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    
                    # Max retries reached
                    logger.error("Max retries reached for rate limit", attempt=attempt)
                    raise
                
                # Other errors
                logger.error("GLM-4.5-Air call failed", error=str(e))
                raise
    
    async def chat_stream(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        temperature: Optional[float] = None
    ):
        """Stream GLM-4.5-Air response with reasoning_content support.
        
        Yields chunks with:
        - type: "reasoning" or "content"
        - content: Chunk text
        
        Args:
            system_prompt: System prompt
            messages: Conversation messages
            temperature: Optional temperature override
            
        Yields:
            Dict with type and content
        """
        logger.info(
            "Starting GLM-4.5-Air stream",
            message_count=len(messages)
        )
        
        # Prepare messages
        full_messages = [
            {"role": "system", "content": system_prompt},
            *messages
        ]
        
        # Use provided temperature or default
        temp = temperature if temperature is not None else self.temperature
        
        try:
            # Stream response (run in thread pool)
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=full_messages,
                max_tokens=self.max_tokens,
                temperature=temp,
                stream=True
            )
            
            # Process stream chunks
            for chunk in response:
                delta = chunk.choices[0].delta
                
                # Check for reasoning_content (GLM-4.5 specific)
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    yield {
                        "type": "reasoning",
                        "content": delta.reasoning_content
                    }
                
                # Check for regular content
                if hasattr(delta, 'content') and delta.content:
                    yield {
                        "type": "content",
                        "content": delta.content
                    }
            
            logger.info("Stream completed")
            
        except Exception as e:
            logger.error("Stream failed", error=str(e))
            raise
    
    async def chat(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """Call GLM-4.5-Air without tools (simple chat).
        
        Args:
            system_prompt: System prompt
            messages: Conversation messages
            temperature: Optional temperature override
            
        Returns:
            Dict with:
                - content: Response text
                - usage: Token usage statistics
        """
        logger.info(
            "Calling GLM-4.5-Air (no tools)",
            message_count=len(messages)
        )
        
        # Prepare messages
        full_messages = [
            {"role": "system", "content": system_prompt},
            *messages
        ]
        
        # Use provided temperature or default
        temp = temperature if temperature is not None else self.temperature
        
        try:
            # Call LLM (run in thread pool)
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=self.model,
                messages=full_messages,
                max_tokens=self.max_tokens,
                temperature=temp
            )
            
            # Parse response
            content = response.choices[0].message.content
            usage = response.usage
            
            logger.info(
                "GLM-4.5-Air response",
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens
            )
            
            return {
                "content": content,
                "usage": {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens
                }
            }
            
        except Exception as e:
            logger.error("Chat failed", error=str(e))
            raise