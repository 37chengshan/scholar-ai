"""Agent Runner execution engine.

Implements D-05 from Agent-Native architecture:
ReAct (Reasoning + Acting) pattern for multi-step agent execution.

Agent Execution Flow:
1. Build context from session
2. THINKING: Call LLM to determine next action
3. TOOL_SELECTION: Extract tool call from LLM response
4. Check permission via Safety Layer
5. TOOL_EXECUTION: Execute tool with parameters
6. Update context and loop until complete
7. Return final answer

Usage:
    runner = AgentRunner(llm_client, registry, context_mgr, safety)
    result = await runner.execute("Find papers about AI", session_id, user_id)
"""

from enum import Enum
from typing import Any, Dict, List, Optional
import litellm
import json

from app.core.tool_registry import ToolRegistry
from app.core.safety_layer import SafetyLayer
from app.core.context_manager import ContextManager, Context
from app.utils.logger import logger


class AgentState(Enum):
    """Agent execution states.
    
    States represent the agent's current phase in the execution loop.
    """
    
    IDLE = "idle"  # Not executing
    THINKING = "thinking"  # Calling LLM to decide action
    TOOL_SELECTION = "tool_selection"  # Parsing tool call from response
    TOOL_EXECUTION = "tool_execution"  # Executing selected tool
    WAITING_CONFIRMATION = "waiting_confirmation"  # Paused for user confirmation
    VERIFYING = "verifying"  # Verifying tool result
    COMPLETED = "completed"  # Task complete, returning answer
    FAILED = "failed"  # Execution failed
    PAUSED = "paused"  # Paused by user


class AgentRunner:
    """Agent execution engine with ReAct pattern.
    
    Implements multi-step reasoning and acting:
    - Call LLM to determine next action (reasoning)
    - Execute tool based on LLM decision (acting)
    - Loop until task complete or max iterations
    
    Attributes:
        llm_client: LLM client (GLM-4.5-Air)
        tool_registry: Tool registry for tool discovery
        context_manager: Context manager for conversation history
        safety_layer: Safety layer for permission checks
        max_iterations: Maximum execution iterations (default: 10)
        current_state: Current agent state
        iteration_count: Current iteration number
    """
    
    def __init__(
        self,
        llm_client: Any,
        tool_registry: ToolRegistry,
        context_manager: ContextManager,
        safety_layer: SafetyLayer,
        max_iterations: int = 10
    ):
        """Initialize Agent Runner.
        
        Args:
            llm_client: LLM client instance
            tool_registry: Tool registry instance
            context_manager: Context manager instance
            safety_layer: Safety layer instance
            max_iterations: Maximum iterations before stopping
        """
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.context_manager = context_manager
        self.safety_layer = safety_layer
        self.max_iterations = max_iterations
        self.current_state = AgentState.IDLE
        self.iteration_count = 0
        
    async def execute(
        self,
        user_input: str,
        session_id: str,
        user_id: str,
        auto_confirm: bool = False
    ) -> Dict[str, Any]:
        """Execute agent task with ReAct pattern.
        
        Main execution loop:
        1. Build context from session
        2. Loop until complete or max iterations:
           a. THINKING: Call LLM with tools
           b. Check if complete -> return answer
           c. TOOL_SELECTION: Extract tool call
           d. Check permission via Safety Layer
           e. If needs_confirmation -> pause
           f. TOOL_EXECUTION: Execute tool
           g. Update context
        3. Return result
        
        Args:
            user_input: User's query or instruction
            session_id: Session ID for context
            user_id: User ID for permission checks
            auto_confirm: Auto-confirm dangerous operations (default: False)
            
        Returns:
            Dict with:
                - success: Whether execution completed successfully
                - answer: Final answer (if completed)
                - tool_calls: List of tool calls made
                - iterations: Number of iterations used
                - state: Final agent state
                - needs_confirmation: (if paused) confirmation request
        """
        logger.info(
            "Agent execution started",
            user_input=user_input[:100],
            session_id=session_id,
            user_id=user_id,
            max_iterations=self.max_iterations
        )
        
        self.current_state = AgentState.THINKING
        self.iteration_count = 0
        
        tool_calls_history: List[Dict[str, Any]] = []
        
        # Build context
        context = await self.context_manager.build_context(session_id)
        context.objective = user_input
        context.environment["user_id"] = user_id
        
        # System prompt for agent
        system_prompt = self._build_system_prompt(context)
        
        # Messages for LLM
        messages = self._build_messages(context, user_input)
        
        # Get tool schemas
        tools_schema = self.tool_registry.list_tools_schema()
        
        try:
            while self.iteration_count < self.max_iterations:
                self.iteration_count += 1
                
                logger.info(
                    "Iteration started",
                    iteration=self.iteration_count,
                    state=self.current_state.value
                )
                
                # THINKING: Call LLM
                self.current_state = AgentState.THINKING
                llm_response = await self._think(system_prompt, messages, tools_schema)
                
                # Check if LLM provided final answer
                if llm_response.get("is_complete", False):
                    self.current_state = AgentState.COMPLETED
                    
                    logger.info(
                        "Agent completed",
                        iterations=self.iteration_count,
                        answer_length=len(llm_response.get("content", ""))
                    )
                    
                    return {
                        "success": True,
                        "answer": llm_response.get("content"),
                        "tool_calls": tool_calls_history,
                        "iterations": self.iteration_count,
                        "state": self.current_state.value
                    }
                
                # TOOL_SELECTION: Extract tool call
                self.current_state = AgentState.TOOL_SELECTION
                tool_call = llm_response.get("tool_call")
                
                if not tool_call:
                    # No tool call, but not complete - treat as error
                    logger.error(
                        "No tool call in LLM response",
                        iteration=self.iteration_count
                    )
                    self.current_state = AgentState.FAILED
                    
                    return {
                        "success": False,
                        "error": "LLM did not provide tool call or final answer",
                        "tool_calls": tool_calls_history,
                        "iterations": self.iteration_count,
                        "state": self.current_state.value
                    }
                
                tool_name = tool_call.get("name")
                tool_parameters = tool_call.get("parameters", {})
                
                logger.info(
                    "Tool selected",
                    tool=tool_name,
                    parameters=tool_parameters
                )
                
                # Check permission
                permission_context = {
                    "user_id": user_id,
                    "session_id": session_id,
                    "tool_name": tool_name,
                    "parameters": tool_parameters
                }
                
                permission_result = await self.safety_layer.check_permission(
                    tool_name,
                    permission_context
                )
                
                # If needs confirmation
                if permission_result.get("needs_confirmation", False):
                    if auto_confirm:
                        # Auto-confirm dangerous operations
                        logger.info(
                            "Auto-confirming dangerous tool",
                            tool=tool_name
                        )
                    else:
                        # Pause for user confirmation
                        self.current_state = AgentState.WAITING_CONFIRMATION
                        
                        logger.info(
                            "Agent paused for confirmation",
                            tool=tool_name,
                            message=permission_result.get("message")
                        )
                        
                        return {
                            "success": False,
                            "needs_confirmation": True,
                            "tool_name": tool_name,
                            "tool_parameters": tool_parameters,
                            "message": permission_result.get("message"),
                            "tool_calls": tool_calls_history,
                            "iterations": self.iteration_count,
                            "state": self.current_state.value
                        }
                
                # TOOL_EXECUTION: Execute tool
                self.current_state = AgentState.TOOL_EXECUTION
                
                tool_result = await self._execute_tool(
                    tool_name,
                    tool_parameters,
                    context
                )
                
                logger.info(
                    "Tool executed",
                    tool=tool_name,
                    success=tool_result.get("success")
                )
                
                # Record tool call
                tool_calls_history.append({
                    "iteration": self.iteration_count,
                    "tool": tool_name,
                    "parameters": tool_parameters,
                    "result": tool_result
                })
                
                # Update context with tool result
                context.tool_history.append({
                    "tool": tool_name,
                    "parameters": tool_parameters,
                    "result": tool_result
                })
                
                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "content": json.dumps(tool_result),
                    "name": tool_name
                })
                
                # Check if tool execution failed
                if not tool_result.get("success", False):
                    # Handle tool execution error
                    error_msg = tool_result.get("error", "Tool execution failed")
                    
                    logger.error(
                        "Tool execution failed",
                        tool=tool_name,
                        error=error_msg
                    )
                    
                    # Special case: Tool not found - fail immediately (cannot recover)
                    if "not found" in error_msg.lower():
                        self.current_state = AgentState.FAILED
                        
                        return {
                            "success": False,
                            "error": error_msg,
                            "tool_calls": tool_calls_history,
                            "iterations": self.iteration_count,
                            "state": self.current_state.value
                        }
                    
                    # Other errors: Add error to messages and continue (let LLM decide how to handle)
                    messages.append({
                        "role": "assistant",
                        "content": f"Tool '{tool_name}' failed: {error_msg}. I'll try a different approach."
                    })
                    
                    # Continue to next iteration
                    continue
            
            # Max iterations reached
            self.current_state = AgentState.FAILED
            
            logger.warning(
                "Max iterations reached",
                iterations=self.iteration_count
            )
            
            return {
                "success": False,
                "error": f"Max iterations ({self.max_iterations}) reached without completion",
                "tool_calls": tool_calls_history,
                "iterations": self.iteration_count,
                "state": self.current_state.value
            }
            
        except Exception as e:
            self.current_state = AgentState.FAILED
            
            logger.error(
                "Agent execution failed",
                error=str(e),
                iteration=self.iteration_count
            )
            
            return {
                "success": False,
                "error": str(e),
                "tool_calls": tool_calls_history,
                "iterations": self.iteration_count,
                "state": self.current_state.value
            }
    
    async def _think(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools_schema: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Call LLM to determine next action.
        
        Args:
            system_prompt: System prompt for agent
            messages: Conversation messages
            tools_schema: Available tool schemas
            
        Returns:
            Dict with:
                - is_complete: Whether LLM provided final answer
                - content: (if complete) Final answer text
                - tool_call: (if not complete) Tool call dict
        """
        try:
            # Call LLM with tools
            response = await litellm.acompletion(
                model="zhipu/glm-4.5-air",
                messages=[
                    {"role": "system", "content": system_prompt},
                    *messages
                ],
                tools=tools_schema,
                tool_choice="auto",
                max_tokens=2048,
                temperature=0.7
            )
            
            # Parse response
            message = response.choices[0].message
            
            # Check if LLM made a tool call
            if message.tool_calls:
                # Extract first tool call
                tool_call = message.tool_calls[0]
                
                return {
                    "is_complete": False,
                    "tool_call": {
                        "name": tool_call.function.name,
                        "parameters": json.loads(tool_call.function.arguments)
                    }
                }
            
            # No tool call - treat as final answer
            content = message.content
            
            return {
                "is_complete": True,
                "content": content
            }
            
        except Exception as e:
            logger.error("LLM call failed", error=str(e))
            raise
    
    async def _execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        context: Context
    ) -> Dict[str, Any]:
        """Execute a tool with parameters.
        
        Args:
            tool_name: Tool to execute
            parameters: Tool parameters
            context: Execution context
            
        Returns:
            Tool result dict with:
                - success: Whether execution succeeded
                - data: (if success) Tool output
                - error: (if failed) Error message
        """
        tool = self.tool_registry.get(tool_name)
        
        if not tool:
            logger.error("Tool not found", tool=tool_name)
            return {
                "success": False,
                "error": f"Tool '{tool_name}' not found in registry"
            }
        
        try:
            # Execute tool via Tool Registry (actual implementation)
            logger.info(
                "Executing tool via registry",
                tool=tool_name,
                parameters=parameters
            )

            result = await self.tool_registry.execute(
                tool_name,
                parameters,
                context=context.environment
            )

            logger.info(
                "Tool execution completed",
                tool=tool_name,
                success=result.get("success")
            )

            return result
            
        except Exception as e:
            logger.error(
                "Tool execution failed",
                tool=tool_name,
                error=str(e)
            )
            
            return {
                "success": False,
                "error": str(e)
            }
    
    async def resume_with_tool(
        self,
        session_id: str,
        tool_name: str,
        parameters: Dict[str, Any],
        confirmed: bool = True
    ) -> Dict[str, Any]:
        """Resume execution after user confirmation.
        
        Args:
            session_id: Session ID
            tool_name: Tool to execute after confirmation
            parameters: Tool parameters
            confirmed: Whether user confirmed (default: True)
            
        Returns:
            Execution result dict
        """
        if not confirmed:
            logger.info("User declined tool execution", tool=tool_name)
            self.current_state = AgentState.PAUSED
            
            return {
                "success": False,
                "error": "User declined tool execution",
                "state": self.current_state.value
            }
        
        logger.info("Resuming with confirmed tool", tool=tool_name)
        
        # Build context
        context = await self.context_manager.build_context(session_id)
        
        # Execute confirmed tool
        self.current_state = AgentState.TOOL_EXECUTION
        tool_result = await self._execute_tool(tool_name, parameters, context)
        
        # Continue execution from this point
        # (Simplified - full implementation would rebuild messages and continue loop)
        
        return {
            "success": tool_result.get("success"),
            "tool_result": tool_result,
            "state": self.current_state.value
        }
    
    def _build_system_prompt(self, context: Context) -> str:
        """Build system prompt for agent.
        
        Args:
            context: Execution context
            
        Returns:
            System prompt string
        """
        objective = context.objective
        
        prompt = f"""You are an intelligent academic assistant helping researchers manage their paper library and research workflow.

User's objective: {objective}

You have access to the following tools:
- external_search: Search external databases (arXiv, Semantic Scholar, CrossRef)
- rag_search: Query user's paper library using RAG
- list_papers: List papers with filters
- read_paper: Read paper details
- list_notes: List user's notes
- read_note: Read note content
- create_note: Create a new note
- update_note: Update an existing note
- upload_paper: Upload a new paper (requires confirmation)
- delete_paper: Delete a paper (requires confirmation)
- extract_references: Extract reference list from papers
- merge_documents: Merge content from multiple sources
- execute_command: Execute system command (requires confirmation)

Your execution strategy:
1. Understand the user's objective
2. Plan which tools to use
3. Execute tools step by step
4. Verify results after each tool
5. Synthesize final answer when objective is achieved

Guidelines:
- Be concise and efficient
- Use minimal tool calls to achieve the objective
- If a tool fails, try alternative approaches
- Provide clear explanations for your actions
- When the objective is complete, provide a final answer

Current environment:
- User ID: {context.environment.get('user_id', 'unknown')}
- Session ID: {context.environment.get('session_id', 'unknown')}
"""
        
        return prompt
    
    def _build_messages(
        self,
        context: Context,
        user_input: str
    ) -> List[Dict[str, Any]]:
        """Build messages list for LLM.
        
        Args:
            context: Execution context
            user_input: Current user input
            
        Returns:
            List of message dicts
        """
        messages = []
        
        # Add important messages from context
        for msg in context.important_messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Add current user input
        messages.append({
            "role": "user",
            "content": user_input
        })
        
        return messages