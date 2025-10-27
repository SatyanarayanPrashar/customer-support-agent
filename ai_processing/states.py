"""
Multi-Agent Supervisor System with Task Decomposition and Routing
Handles complex queries by splitting them into subtasks and routing to specialized agents
"""

from typing import Annotated, Literal, TypedDict, List, Optional
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from enum import Enum
import operator

class TaskStatus(str, Enum):
    """Status of individual tasks"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"             # Waiting for human input
    FAILED = "failed"

class SubTask(TypedDict):
    """Individual subtask that needs to be executed"""
    task_id: str
    description: str
    agent: str                      # Which agent should handle this
    status: TaskStatus
    result: Optional[str]           # Result from the agent
    dependencies: List[str]         # Task IDs that must complete first
    priority: int                   # Lower number = higher priority

class AgentState(TypedDict):
    """
    The main state that flows through the graph.
    
    This state captures:
    - The conversation history
    - The original user query
    - Decomposed subtasks
    - Current active task
    - Routing decisions
    - Human-in-the-loop requirements
    """
    # Conversation history
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Original user query
    original_query: str
    
    # Task decomposition
    subtasks: List[SubTask]
    
    # Current task being processed
    current_task: Optional[SubTask]
    
    # Next agent to route to
    next_agent: str
    
    # Human intervention flag
    needs_human_input: bool
    human_input_prompt: Optional[str]  # What to ask the user
    
    # Context from previous agents (for passing info between agents)
    agent_context: dict
    
    # Completion tracking
    all_tasks_completed: bool
    
    # Final response to user
    final_response: Optional[str]

class AgentType(str, Enum):
    """Available agent types"""
    SUPERVISOR = "supervisor"
    TROUBLESHOOT = "troubleshoot"
    BILLING = "billing"
    WARRANTY = "warranty"
    RETURNS = "returns"  # Suggested: Handle return requests
    ACCOUNT = "account"  # Suggested: Account management, password resets
    TECHNICAL_SPECS = "technical_specs"  # Suggested: Product specifications
    FEEDBACK = "feedback"  # Suggested: Collect feedback and complaints
