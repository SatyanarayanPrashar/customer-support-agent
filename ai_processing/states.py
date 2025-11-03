"""
Multi-Agent Supervisor System with Task Decomposition and Routing
Handles complex queries by splitting them into subtasks and routing to specialized agents
"""

from typing import Annotated, TypedDict, List, Optional
from langgraph.graph import END, START
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from enum import Enum

from ai_processing.get_response import Get_response

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

class UserInfo(TypedDict):
    """User information relevant to the support session"""
    user_id: str
    phone_number: str
    name: Optional[str]
    email: Optional[str]
    account_created: Optional[str]  # Date string
    purchase_history: Optional[List[dict]]  # List of past purchases

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
    messages: Annotated[List[BaseMessage], add_messages]        # Conversation history
    original_query: str                                         # Original user query

    subtasks: List[SubTask]                                     # Task decomposition
    current_task: Optional[SubTask]                             # Current task being processed
    
    next_agent: str                                             # Next agent to route to
    
    needs_human_input: bool                                     # Human intervention flag
    human_input_prompt: Optional[str]                           # What to ask the user
    
    agent_context: dict                                         # Context from previous agents (for passing info between agents)
    
    all_tasks_completed: bool                                   # Completion tracking
    
    final_response: Optional[str]                               # Final response to user
    llm_client: Optional[Get_response]                          # LLM client for supervisor

    # casual_turn_count: int                                      # Track number of casual exchanges
    # awaiting_real_query: bool                                   # Flag if waiting for actionable request

class AgentType(str, Enum):
    """Available agent types"""
    SUPERVISOR = "supervisor"
    TROUBLESHOOT = "troubleshoot"
    BILLING = "billing"
    WARRANTY = "warranty"
    RETURNS = "returns"
