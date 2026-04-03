"""Tool Registry for Agent tools.

Provides centralized registration, discovery, and schema generation for Agent tools.

Implements D-06 from Agent-Native architecture:
- Tool registration and retrieval
- Schema generation for LLM function calling
- Permission checking for tools requiring confirmation

Usage:
    registry = ToolRegistry()
    tool = registry.get("external_search")
    schemas = registry.list_tools_schema()
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class Tool(BaseModel):
    """Tool definition for Agent use.
    
    Attributes:
        name: Unique tool identifier
        description: Human-readable description for LLM
        parameters: JSON Schema of parameters
        needs_confirmation: Whether tool requires user confirmation (dangerous operations)
    """
    
    model_config = ConfigDict(use_enum_values=True)
    
    name: str
    description: str
    parameters: Dict[str, Any]
    needs_confirmation: bool = False


class ToolRegistry:
    """Centralized tool registry for Agent tools.
    
    Manages tool registration, discovery, and schema generation.
    Implements D-06: Tool Registry design from Agent-Native architecture.
    
    Attributes:
        tools: Dictionary mapping tool names to Tool objects
    """
    
    def __init__(self):
        """Initialize ToolRegistry with default tools."""
        self.tools: Dict[str, Tool] = {}
        self._register_default_tools()
    
    def register(self, tool: Tool) -> None:
        """Register a tool.
        
        Args:
            tool: Tool object to register
        """
        self.tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool object if found, None otherwise
        """
        return self.tools.get(name)
    
    def list_all(self) -> List[Tool]:
        """List all registered tools.
        
        Returns:
            List of all Tool objects
        """
        return list(self.tools.values())
    
    def needs_confirmation(self, tool_name: str) -> bool:
        """Check if a tool needs user confirmation.
        
        Args:
            tool_name: Tool name to check
            
        Returns:
            True if tool needs confirmation, False otherwise
        """
        tool = self.get(tool_name)
        return tool.needs_confirmation if tool else False
    
    def list_tools_schema(self) -> List[Dict[str, Any]]:
        """Generate LLM-compatible tool schemas (OpenAI Functions format).
        
        Returns:
            List of tool schemas in OpenAI Functions format
        """
        schemas = []
        
        for tool in self.tools.values():
            schema = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            }
            
            # Add parameters
            for param_name, param in tool.parameters.items():
                schema["function"]["parameters"]["properties"][param_name] = {
                    "type": param.get("type", "string"),
                    "description": param.get("description", "")
                }
                
                if param.get("enum"):
                    schema["function"]["parameters"]["properties"][param_name]["enum"] = param["enum"]
                
                if param.get("required"):
                    schema["function"]["parameters"]["required"].append(param_name)
            
            schemas.append(schema)
        
        return schemas
    
    def _register_default_tools(self) -> None:
        """Register the default set of 15+ tools.
        
        Tool categories:
        - Query Tools (6): external_search, rag_search, list_papers, read_paper, list_notes, read_note
        - Note Tools (3): create_note, update_note
        - Paper Tools (2): upload_paper, delete_paper
        - Advanced Tools (3): extract_references, merge_documents, execute_command
        
        Permission levels:
        - Level 1 (READ): Auto-execute, no confirmation
        - Level 2 (WRITE): Log audit, no confirmation
        - Level 3 (DANGEROUS): Requires confirmation
        """
        # Query Tools (Level 1: READ)
        self.register(Tool(
            name="external_search",
            description="Search external academic databases (arXiv, Semantic Scholar, CrossRef)",
            parameters={
                "query": {
                    "type": "string",
                    "description": "Search keywords",
                    "required": True
                },
                "sources": {
                    "type": "array",
                    "description": "Search sources",
                    "required": False,
                    "default": ["arxiv", "semantic_scholar"],
                    "enum": ["arxiv", "semantic_scholar", "crossref"]
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return",
                    "required": False,
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50
                }
            },
            needs_confirmation=False
        ))
        
        self.register(Tool(
            name="rag_search",
            description="Query user's paper library using RAG (Retrieval-Augmented Generation)",
            parameters={
                "question": {
                    "type": "string",
                    "description": "Question to ask",
                    "required": True
                },
                "paper_ids": {
                    "type": "array",
                    "description": "Paper IDs to search (optional, searches all if empty)",
                    "required": False,
                    "default": []
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of top results to return",
                    "required": False,
                    "default": 5
                }
            },
            needs_confirmation=False
        ))
        
        self.register(Tool(
            name="list_papers",
            description="List papers in user's library with optional filters",
            parameters={
                "filter": {
                    "type": "object",
                    "description": "Filter criteria",
                    "required": False,
                    "default": {}
                },
                "sort": {
                    "type": "string",
                    "description": "Sort field",
                    "required": False,
                    "default": "created_at",
                    "enum": ["created_at", "year", "title"]
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return",
                    "required": False,
                    "default": 20
                }
            },
            needs_confirmation=False
        ))
        
        self.register(Tool(
            name="read_paper",
            description="Read paper details (title, abstract, content, notes)",
            parameters={
                "paper_id": {
                    "type": "string",
                    "description": "Paper ID",
                    "required": True
                },
                "sections": {
                    "type": "array",
                    "description": "Sections to retrieve",
                    "required": False,
                    "default": ["metadata", "abstract"],
                    "enum": ["metadata", "abstract", "content", "notes", "chunks"]
                }
            },
            needs_confirmation=False
        ))
        
        self.register(Tool(
            name="list_notes",
            description="List all user's notes",
            parameters={
                "filter": {
                    "type": "object",
                    "description": "Filter criteria",
                    "required": False,
                    "default": {}
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum results to return",
                    "required": False,
                    "default": 20
                }
            },
            needs_confirmation=False
        ))
        
        self.register(Tool(
            name="read_note",
            description="Read note content",
            parameters={
                "note_id": {
                    "type": "string",
                    "description": "Note ID",
                    "required": True
                }
            },
            needs_confirmation=False
        ))
        
        # Note Tools (Level 2: WRITE)
        self.register(Tool(
            name="create_note",
            description="Create a new note (can be standalone or linked to papers)",
            parameters={
                "title": {
                    "type": "string",
                    "description": "Note title",
                    "required": True
                },
                "content": {
                    "type": "string",
                    "description": "Note content (Markdown format)",
                    "required": True
                },
                "paper_ids": {
                    "type": "array",
                    "description": "Linked paper IDs (optional)",
                    "required": False,
                    "default": []
                },
                "tags": {
                    "type": "array",
                    "description": "Tags for the note",
                    "required": False,
                    "default": []
                }
            },
            needs_confirmation=False
        ))
        
        self.register(Tool(
            name="update_note",
            description="Update an existing note",
            parameters={
                "note_id": {
                    "type": "string",
                    "description": "Note ID",
                    "required": True
                },
                "updates": {
                    "type": "object",
                    "description": "Fields to update",
                    "required": True
                }
            },
            needs_confirmation=False
        ))
        
        # Paper Tools (Level 3: DANGEROUS)
        self.register(Tool(
            name="upload_paper",
            description="Upload a new paper to the library",
            parameters={
                "source": {
                    "type": "object",
                    "description": "Paper source",
                    "required": True
                },
                "metadata": {
                    "type": "object",
                    "description": "Optional metadata override",
                    "required": False,
                    "default": {}
                }
            },
            needs_confirmation=True
        ))
        
        self.register(Tool(
            name="delete_paper",
            description="Delete a paper from the library",
            parameters={
                "paper_id": {
                    "type": "string",
                    "description": "Paper ID to delete",
                    "required": True
                }
            },
            needs_confirmation=True
        ))
        
        # Advanced Tools (Level 2-3)
        self.register(Tool(
            name="extract_references",
            description="Extract reference list from papers",
            parameters={
                "paper_ids": {
                    "type": "array",
                    "description": "Paper IDs",
                    "required": True
                },
                "format": {
                    "type": "string",
                    "description": "Citation format",
                    "required": False,
                    "default": "apa",
                    "enum": ["apa", "mla", "chicago", "bibtex"]
                }
            },
            needs_confirmation=False
        ))
        
        self.register(Tool(
            name="merge_documents",
            description="Merge content from multiple sources into one document",
            parameters={
                "sources": {
                    "type": "array",
                    "description": "Sources to merge",
                    "required": True
                },
                "output_format": {
                    "type": "string",
                    "description": "Output format",
                    "required": False,
                    "default": "markdown",
                    "enum": ["markdown", "json", "txt"]
                },
                "title": {
                    "type": "string",
                    "description": "Output document title",
                    "required": False
                }
            },
            needs_confirmation=False
        ))
        
        self.register(Tool(
            name="execute_command",
            description="Execute a system command (e.g., file operations, format conversion)",
            parameters={
                "command": {
                    "type": "string",
                    "description": "Command name",
                    "required": True
                },
                "args": {
                    "type": "array",
                    "description": "Command arguments",
                    "required": False,
                    "default": []
                }
            },
            needs_confirmation=True
        ))
        
        # Additional helper tools
        self.register(Tool(
            name="ask_user_confirmation",
            description="Request user confirmation for an operation",
            parameters={
                "message": {
                    "type": "string",
                    "description": "Confirmation message",
                    "required": True
                },
                "details": {
                    "type": "object",
                    "description": "Operation details",
                    "required": False
                }
            },
            needs_confirmation=False
        ))
        
        self.register(Tool(
            name="show_message",
            description="Display information or progress to user (non-blocking)",
            parameters={
                "message": {
                    "type": "string",
                    "description": "Message to display",
                    "required": True
                },
                "type": {
                    "type": "string",
                    "description": "Message type",
                    "required": False,
                    "default": "info",
                    "enum": ["info", "warning", "success", "progress"]
                }
            },
            needs_confirmation=False
        ))