"""
Multi-Agent Supervisor System with Task Decomposition and Routing
Handles complex queries by splitting them into subtasks and routing to specialized agents
"""

from typing import Annotated, Literal, TypedDict, List, Optional, Dict, Any
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from enum import Enum
import operator
import json
import openai
from utils.config_loader import load_config
from utils.logger import get_logger

logger = get_logger()
config = load_config("config.yaml")

# ===========================
# LLM Interface
# ===========================

class Get_response:
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize AIWorker with configuration.
        """
        self.model_name: str = config['ai_processing']['model']
        self.api_key: str = config['api_keys']['openai_api']
        self.temperature: float = config['ai_processing'].get('temperature', 0.7)

        # Initialize the client
        self.client = self._init_client()

        # Load system prompt from file
        self.system_prompt: str = self._load_system_prompt()

        self.max_retries = 3
        self.retry_delay = 2  # seconds

    def _init_client(self):
        """
        Initializes the GenAI client.
        """
        return openai.OpenAI(
            api_key=self.api_key
        )
    
    def _load_system_prompt(self) -> str:
        """
        Load system prompt from file or return default.
        """
        try:
            with open('prompts/system_prompt.txt', 'r') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning("System prompt file not found, using default")
            return "You are a helpful AI assistant."

    def invoke(self, conversation: list):
        """
        Generate response from the AI.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=conversation,
                temperature=self.temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating text: {e}")
            return ""


# ===========================
# State Definition
# ===========================

class TaskStatus(str, Enum):
    """Status of individual tasks"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"  # Waiting for human input
    FAILED = "failed"


class SubTask(TypedDict):
    """Individual subtask that needs to be executed"""
    task_id: str
    description: str
    agent: str  # Which agent should handle this
    status: TaskStatus
    result: Optional[str]  # Result from the agent
    dependencies: List[str]  # Task IDs that must complete first
    priority: int  # Lower number = higher priority


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
    
    # LLM client for supervisor
    llm_client: Optional[Get_response]
    
    # Casual conversation tracking
    casual_turn_count: int  # Track number of casual exchanges
    awaiting_real_query: bool  # Flag if waiting for actionable request


# ===========================
# Agent Definitions
# ===========================

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


# ===========================
# Supervisor Prompts
# ===========================

SUPERVISOR_DECOMPOSITION_PROMPT = """You are a supervisor agent in a customer support system. Your job is to analyze customer queries and break them down into specific subtasks that can be handled by specialized agents.

Available Agents:
- troubleshoot: Diagnoses and resolves product issues, technical problems
- billing: Handles payments, invoices, refunds, charges
- warranty: Checks warranty status, coverage, and claims
- returns: Processes return and exchange requests
- account: Manages account settings, passwords, profile updates
- technical_specs: Provides product specifications and compatibility info
- feedback: Collects customer feedback and complaints

Your task:
1. First, determine if this is a CASUAL MESSAGE (greetings, small talk, thanks) or an ACTIONABLE REQUEST
2. If CASUAL: Return an empty array []
3. If ACTIONABLE: Analyze the query and create subtasks

Customer Query: {query}

IMPORTANT RULES:
- Greetings like "hi", "hello", "hey" → Return []
- Thank you messages → Return []
- Casual conversation → Return []
- Only create tasks for SPECIFIC ACTIONABLE REQUESTS that require agent assistance

If actionable, respond with a JSON array in this format:
[
  {{
    "task_id": "task_1",
    "description": "brief description of what needs to be done",
    "agent": "agent_name",
    "dependencies": [],
    "priority": 1
  }}
]

Examples:
- "hi" → []
- "hello there" → []
- "thanks!" → []
- "my product is broken" → [task with troubleshoot agent]
- "what's my warranty status?" → [task with warranty agent]

Respond ONLY with the JSON array (or empty array), no additional text."""

SUPERVISOR_ROUTING_PROMPT = """You are a supervisor agent routing the next task.

Current situation:
- Completed tasks: {completed_tasks}
- Remaining pending tasks: {pending_tasks}
- Agent context: {agent_context}

Based on the completed tasks and remaining tasks, provide a brief message to the user explaining what will happen next.

Keep it conversational and brief (1-2 sentences). Examples:
- "Let me check that for you."
- "Now let me look into your warranty status."
- "I'll help you process that return."

Respond with ONLY the message, no additional formatting."""


# ===========================
# Supervisor Node with LLM
# ===========================

def supervisor_node(state: AgentState) -> AgentState:
    """
    The supervisor agent that:
    1. Analyzes the user query using LLM
    2. Decomposes it into subtasks (or handles casual conversation)
    3. Determines task dependencies and order
    4. Routes to the next available agent
    5. Manages casual conversation turns
    """
    
    llm_client = state.get("llm_client")
    
    if not llm_client:
        logger.error("LLM client not found in state")
        state["all_tasks_completed"] = True
        state["next_agent"] = "finish"
        state["final_response"] = "Error: System not properly configured."
        return state
    
    # Initialize casual turn tracking if not present
    if "casual_turn_count" not in state:
        state["casual_turn_count"] = 0
    if "awaiting_real_query" not in state:
        state["awaiting_real_query"] = False
    
    # If this is the first time supervisor is called
    if not state.get("subtasks"):
        logger.info("Analyzing user query")
        
        # Decompose the query into subtasks using LLM
        # This returns (subtasks_list, unactionable_message)
        subtasks, unactionable_msg = decompose_query_with_llm(state["original_query"], llm_client)
        
        # If no tasks (casual conversation), handle it
        if not subtasks:
            logger.info("Casual conversation detected, no tasks created")
            state["casual_turn_count"] += 1
            
            # Use the LLM-generated unactionable message if available
            if unactionable_msg:
                response = unactionable_msg
            else:
                # Generate response based on turn count (fallback)
                if state["casual_turn_count"] == 1:
                    response = generate_welcome_with_capabilities(llm_client)
                elif state["casual_turn_count"] == 2:
                    response = generate_helpful_prompt(llm_client)
                elif state["casual_turn_count"] >= 3:
                    response = generate_final_prompt(state["casual_turn_count"], llm_client)
            
            state["messages"].append(AIMessage(content=response))
            state["all_tasks_completed"] = True
            state["next_agent"] = "finish"
            state["final_response"] = response
            state["awaiting_real_query"] = True
            return state
        
        # Real tasks detected - reset casual counters
        state["casual_turn_count"] = 0
        state["awaiting_real_query"] = False
        state["subtasks"] = subtasks
        logger.info(f"Generated {len(subtasks)} subtasks")
    
    # Find the next task to execute
    next_task = get_next_task(state["subtasks"])
    
    if next_task is None:
        # All tasks completed
        logger.info("All tasks completed")
        state["all_tasks_completed"] = True
        state["next_agent"] = "finish"
        state["final_response"] = compile_final_response_with_llm(state, llm_client)
    else:
        # Update task status
        for task in state["subtasks"]:
            if task["task_id"] == next_task["task_id"]:
                task["status"] = TaskStatus.IN_PROGRESS
        
        state["current_task"] = next_task
        state["next_agent"] = next_task["agent"]
        
        # Generate routing message using LLM
        routing_message = generate_routing_message(state, llm_client)
        
        # Add supervisor message explaining what we're doing
        state["messages"].append(AIMessage(content=routing_message))
        
        logger.info(f"Routing to {next_task['agent']} for: {next_task['description']}")
    
    return state


def generate_welcome_with_capabilities(llm_client: Get_response) -> str:
    """
    Generate a welcoming response that showcases system capabilities.
    Used on first casual interaction.
    """
    
    try:
        prompt = """Generate a friendly greeting for a customer support chatbot that:
1. Welcomes the user warmly
2. Lists the key things you can help with (troubleshooting, billing, warranty, returns, account management)
3. Asks what they need help with
4. Keep it conversational and brief (3-4 sentences)

Example tone: "Hi there! I'm here to help you with product issues, billing questions, warranty information, returns, and account management. What can I assist you with today?"
"""
        
        conversation = [
            {"role": "system", "content": "You are a friendly customer support agent introducing your capabilities."},
            {"role": "user", "content": prompt}
        ]
        
        response = llm_client.invoke(conversation)
        return response.strip()
        
    except Exception as e:
        logger.error(f"Error generating welcome: {e}")
        return "Hello! I can help you with product troubleshooting, billing questions, warranty information, returns, and account management. What do you need help with today?"


def generate_helpful_prompt(llm_client: Get_response) -> str:
    """
    Generate a more specific prompt for the second casual turn.
    """
    
    try:
        prompt = """The user hasn't yet asked a specific question. Generate a friendly but slightly more specific prompt that:
1. Acknowledges they might be browsing
2. Gives specific examples of what you can help with
3. Encourages them to ask a question
4. Keep it brief (2-3 sentences)

Example: "I'm here whenever you're ready! For example, I can help troubleshoot a device that's not working, check your warranty status, or answer billing questions. What would you like to know?"
"""
        
        conversation = [
            {"role": "system", "content": "You are a friendly customer support agent."},
            {"role": "user", "content": prompt}
        ]
        
        response = llm_client.invoke(conversation)
        return response.strip()
        
    except Exception as e:
        logger.error(f"Error generating helpful prompt: {e}")
        return "I'm here to help! For example, I can troubleshoot issues, check warranty status, or answer billing questions. What would you like to know?"


def generate_final_prompt(turn_count: int, llm_client: Get_response) -> str:
    """
    Generate a more direct prompt after multiple casual turns.
    After 3+ turns without a real question, be more explicit.
    """
    
    try:
        if turn_count >= 4:
            # After 4+ turns, suggest they come back later
            prompt = """The user has made several casual messages without asking for help. Generate a polite message that:
1. Acknowledges they might not need help right now
2. Invites them to come back when they do
3. Remains friendly and welcoming
4. Keep it brief (1-2 sentences)

Example: "It looks like you might not need assistance right now. Feel free to reach out whenever you have a question!"
"""
        else:
            # Turn 3 - be direct but helpful
            prompt = """The user has said casual things but hasn't asked a specific question yet. Generate a direct but friendly message that:
1. Politely asks what specific issue they need help with
2. Reminds them of key capabilities
3. Keep it brief (2 sentences)

Example: "I'd love to help! Could you let me know what specific issue you're experiencing or what question you have?"
"""
        
        conversation = [
            {"role": "system", "content": "You are a friendly but direct customer support agent."},
            {"role": "user", "content": prompt}
        ]
        
        response = llm_client.invoke(conversation)
        return response.strip()
        
    except Exception as e:
        logger.error(f"Error generating final prompt: {e}")
        if turn_count >= 4:
            return "It looks like you might not need assistance right now. Feel free to reach out whenever you have a question!"
        else:
            return "I'd love to help! Could you let me know what specific issue you're experiencing?"


def generate_casual_response(query: str, llm_client: Get_response) -> str:
    """
    Generate a friendly response for casual conversation (greetings, thanks, etc.)
    DEPRECATED: Use turn-based responses instead
    """
    
    try:
        prompt = f"""You are a friendly customer support agent. The user said: "{query}"

This is a casual message (greeting, thanks, small talk) - not a support request.

Respond warmly and ask how you can help them today. Keep it brief (1-2 sentences).

Examples:
- User: "hi" → "Hi! How can I help you today?"
- User: "hello" → "Hello! What can I assist you with?"
- User: "thanks" → "You're welcome! Is there anything else I can help you with?"
"""
        
        conversation = [
            {"role": "system", "content": "You are a friendly customer support agent."},
            {"role": "user", "content": prompt}
        ]
        
        response = llm_client.invoke(conversation)
        return response.strip()
        
    except Exception as e:
        logger.error(f"Error generating casual response: {e}")
        return "Hello! How can I help you today?"


def decompose_query_with_llm(query: str, llm_client: Get_response) -> tuple[List[SubTask], Optional[str]]:
    """
    Use LLM to decompose the user query into subtasks.
    Returns (subtasks_list, unactionable_message).
    
    - If query is actionable: returns ([subtasks], None)
    - If query is casual/unactionable: returns ([], "LLM generated message")
    """
    
    try:
        # Prepare the conversation for LLM
        conversation = [
            {"role": "system", "content": "You are an expert at analyzing customer support queries and breaking them into actionable tasks."},
            {"role": "user", "content": SUPERVISOR_DECOMPOSITION_PROMPT.format(query=query)}
        ]
        
        # Get LLM response
        response = llm_client.invoke(conversation)
        logger.debug(f"LLM decomposition response: {response}")
        
        # Clean response - remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        # Parse JSON response
        data = json.loads(response)
        
        # Case 1: LLM returned an unactionable message (dict with 'response' key)
        if isinstance(data, dict) and "response" in data:
            logger.info("LLM detected casual/unactionable query")
            unactionable_message = data["response"]
            return ([], unactionable_message)
        
        # Case 2: LLM returned empty array (casual conversation)
        if isinstance(data, list) and len(data) == 0:
            logger.info("Empty task list - casual conversation")
            return ([], None)
        
        # Case 3: LLM returned actionable subtasks (list with items)
        if isinstance(data, list):
            subtasks = []
            for task_data in data:
                subtask = SubTask(
                    task_id=task_data["task_id"],
                    description=task_data["description"],
                    agent=task_data["agent"],
                    status=TaskStatus.PENDING,
                    result=None,
                    dependencies=task_data.get("dependencies", []),
                    priority=task_data.get("priority", 1)
                )
                subtasks.append(subtask)
            
            logger.info(f"Generated {len(subtasks)} actionable subtasks")
            return (subtasks, None)
        
        # Unexpected JSON format
        logger.error(f"Unexpected JSON format from LLM: {type(data)}")
        return ([], None)
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.error(f"Response was: {response}")
        return ([], None)
    except Exception as e:
        logger.error(f"Error in decompose_query_with_llm: {e}")
        return ([], None)


def generate_routing_message(state: AgentState, llm_client: Get_response) -> str:
    """
    Generate a natural message explaining what the supervisor is doing next.
    """
    
    try:
        completed_tasks = [t for t in state["subtasks"] if t["status"] == TaskStatus.COMPLETED]
        pending_tasks = [t for t in state["subtasks"] if t["status"] == TaskStatus.PENDING]
        
        completed_desc = [t["description"] for t in completed_tasks]
        pending_desc = [t["description"] for t in pending_tasks]
        
        conversation = [
            {"role": "system", "content": "You are a friendly customer support supervisor."},
            {"role": "user", "content": SUPERVISOR_ROUTING_PROMPT.format(
                completed_tasks=completed_desc,
                pending_tasks=pending_desc,
                agent_context=state.get("agent_context", {})
            )}
        ]
        
        response = llm_client.invoke(conversation)
        return response.strip()
        
    except Exception as e:
        logger.error(f"Error generating routing message: {e}")
        # Fallback to simple message
        return f"Let me {state['current_task']['description']}."


def compile_final_response_with_llm(state: AgentState, llm_client: Get_response) -> str:
    """
    Compile results from all agents into a final response using LLM.
    """
    
    try:
        completed_tasks = [t for t in state["subtasks"] if t["status"] == TaskStatus.COMPLETED]
        
        task_summaries = []
        for task in completed_tasks:
            task_summaries.append(f"- {task['description']}: {task['result']}")
        
        prompt = f"""You are concluding a customer support conversation. Summarize the assistance provided in a friendly, professional manner.

Tasks completed:
{chr(10).join(task_summaries)}

Create a brief, warm closing message that:
1. Summarizes what was addressed
2. Offers further assistance
3. Sounds natural and helpful

Keep it concise (2-3 sentences)."""
        
        conversation = [
            {"role": "system", "content": "You are a helpful customer support agent."},
            {"role": "user", "content": prompt}
        ]
        
        response = llm_client.invoke(conversation)
        return response.strip()
        
    except Exception as e:
        logger.error(f"Error compiling final response: {e}")
        # Fallback response
        return "I've addressed your concerns. Is there anything else I can help you with?"


def get_next_task(subtasks: List[SubTask]) -> Optional[SubTask]:
    """
    Get the next task that should be executed based on:
    1. Dependencies (all dependent tasks must be completed)
    2. Priority (lower number = higher priority)
    3. Status (only pending tasks)
    """
    
    available_tasks = []
    
    for task in subtasks:
        # Skip if not pending
        if task["status"] != TaskStatus.PENDING:
            continue
        
        # Check if all dependencies are completed
        dependencies_met = True
        for dep_id in task["dependencies"]:
            dep_task = next((t for t in subtasks if t["task_id"] == dep_id), None)
            if dep_task and dep_task["status"] != TaskStatus.COMPLETED:
                dependencies_met = False
                break
        
        if dependencies_met:
            available_tasks.append(task)
    
    # Sort by priority and return the highest priority task
    if available_tasks:
        return sorted(available_tasks, key=lambda x: x["priority"])[0]
    
    return None


def compile_final_response(state: AgentState) -> str:
    """Compile results from all agents into a final response (fallback without LLM)"""
    
    response_parts = ["Here's a summary of what we've addressed:\n"]
    
    for task in state["subtasks"]:
        if task["status"] == TaskStatus.COMPLETED and task["result"]:
            response_parts.append(f"- {task['description'].capitalize()}: {task['result']}")
    
    response_parts.append("\nIs there anything else I can help you with?")
    
    return "\n".join(response_parts)


# ===========================
# Specialized Agent Nodes
# ===========================

def troubleshoot_agent(state: AgentState) -> AgentState:
    """
    Troubleshooting agent - diagnoses and resolves product issues
    """
    
    # In production, this would use an LLM with troubleshooting knowledge
    # May also query a vector database of known issues and solutions
    
    current_task = state["current_task"]
    
    # Check if we need more information from the user
    if "product_model" not in state["agent_context"]:
        # For now, we'll skip human input to avoid complexity
        # In production, you'd implement proper human-in-the-loop here
        state["agent_context"]["product_model"] = "Unknown"
    
    # Perform troubleshooting
    result = "I've analyzed the issue. Try these steps: 1) Restart the device, 2) Check connections, 3) Update firmware."
    
    # Update task status
    for task in state["subtasks"]:
        if task["task_id"] == current_task["task_id"]:
            task["status"] = TaskStatus.COMPLETED
            task["result"] = result
    
    # Add context for other agents
    state["agent_context"]["troubleshoot_completed"] = True
    state["agent_context"]["issue_resolved"] = False  # Would be determined by actual logic
    
    # Add message
    state["messages"].append(AIMessage(content=result))
    
    # Clear current task
    state["current_task"] = None
    
    return state


def billing_agent(state: AgentState) -> AgentState:
    """
    Billing agent - handles payment, invoices, refunds
    """
    
    current_task = state["current_task"]
    
    # Simulate billing logic
    result = "I've reviewed your billing. Your last payment of $99.99 was processed on Oct 15. No outstanding balance."
    
    # Update task
    for task in state["subtasks"]:
        if task["task_id"] == current_task["task_id"]:
            task["status"] = TaskStatus.COMPLETED
            task["result"] = result
    
    state["messages"].append(AIMessage(content=result))
    state["current_task"] = None
    
    return state


def warranty_agent(state: AgentState) -> AgentState:
    """
    Warranty agent - checks warranty status and coverage
    """
    
    current_task = state["current_task"]
    
    # Check if product needs replacement based on troubleshoot results
    issue_context = ""
    if state["agent_context"].get("issue_resolved") == False:
        issue_context = " Since troubleshooting didn't resolve the issue, you may be eligible for a replacement."
    
    # Simulate warranty check
    result = f"Your product is under warranty until Dec 2025. It covers manufacturing defects.{issue_context}"
    
    # Update task
    for task in state["subtasks"]:
        if task["task_id"] == current_task["task_id"]:
            task["status"] = TaskStatus.COMPLETED
            task["result"] = result
    
    state["messages"].append(AIMessage(content=result))
    state["current_task"] = None
    
    return state


def returns_agent(state: AgentState) -> AgentState:
    """
    Returns agent - processes return and exchange requests
    """
    
    current_task = state["current_task"]
    
    result = "I can help you with a return. You have 30 days from purchase. I'll email you a return label."
    
    for task in state["subtasks"]:
        if task["task_id"] == current_task["task_id"]:
            task["status"] = TaskStatus.COMPLETED
            task["result"] = result
    
    state["messages"].append(AIMessage(content=result))
    state["current_task"] = None
    
    return state


# ===========================
# Human-in-the-Loop Node
# ===========================

def human_input_node(state: AgentState) -> AgentState:
    """
    Handle human input requests.
    This is where the graph pauses and waits for user input.
    """
    
    # In production, this would integrate with your chat interface
    # to collect and return the user's response
    
    if state.get("human_input_prompt"):
        state["messages"].append(AIMessage(content=state["human_input_prompt"]))
    
    # The graph will interrupt here for human input
    # When resumed, the user's response will be in the latest message
    
    return state


# ===========================
# Routing Function
# ===========================

def route_to_agent(state: AgentState) -> str:
    """
    Determine which node to go to next based on state.
    Only called from supervisor node.
    """
    
    # Route based on next_agent
    next_agent = state.get("next_agent", "")
    
    if next_agent == "finish" or state.get("all_tasks_completed"):
        return "finish"
    
    if next_agent in [AgentType.TROUBLESHOOT, AgentType.BILLING, 
                      AgentType.WARRANTY, AgentType.RETURNS]:
        return next_agent
    
    # Default to end if no valid routing
    return "finish"


# ===========================
# Graph Construction
# ===========================

def create_support_graph():
    """
    Create the LangGraph workflow for the multi-agent system
    """
    
    # Initialize the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("troubleshoot", troubleshoot_agent)
    workflow.add_node("billing", billing_agent)
    workflow.add_node("warranty", warranty_agent)
    workflow.add_node("returns", returns_agent)
    workflow.add_node("human_input", human_input_node)
    
    # Add edges
    workflow.add_edge(START, "supervisor")
    
    # Add conditional edges from supervisor to all possible next nodes
    workflow.add_conditional_edges(
        "supervisor",
        route_to_agent,
        {
            "troubleshoot": "troubleshoot",
            "billing": "billing",
            "warranty": "warranty",
            "returns": "returns",
            "finish": END
        }
    )
    
    # All agents route back to supervisor
    workflow.add_edge("troubleshoot", "supervisor")
    workflow.add_edge("billing", "supervisor")
    workflow.add_edge("warranty", "supervisor")
    workflow.add_edge("returns", "supervisor")
    
    # Human input routes back to supervisor
    workflow.add_edge("human_input", "supervisor")
    
    return workflow.compile()


# ===========================
# Usage Example
# ===========================

def run_support_system(config: Dict[str, Any], user_query: str):
    """
    Example usage of the multi-agent support system with LLM integration
    
    Args:
        config: Configuration dictionary with API keys and model settings
        user_query: The user's support query
    """
    
    # Initialize LLM client
    llm_client = Get_response(config)
    
    # Create the graph
    graph = create_support_graph()
    
    # Initialize state with a complex query
    initial_state = AgentState(
        messages=[HumanMessage(content=user_query)],
        original_query=user_query,
        subtasks=[],
        current_task=None,
        next_agent="supervisor",
        needs_human_input=False,
        human_input_prompt=None,
        agent_context={},
        all_tasks_completed=False,
        final_response=None,
        llm_client=llm_client
    )
    
    # Run the graph
    logger.info("Starting multi-agent support system...")
    logger.info(f"User Query: {user_query}\n")
    
    try:
        # Execute the graph
        result = graph.invoke(initial_state)
        
        # Print conversation
        print("\n" + "="*60)
        print("CONVERSATION FLOW")
        print("="*60)
        for msg in result["messages"]:
            role = "User" if isinstance(msg, HumanMessage) else "Assistant"
            print(f"\n{role}: {msg.content}")
        
        # Print task breakdown
        print("\n" + "="*60)
        print("TASK BREAKDOWN")
        print("="*60)
        for task in result["subtasks"]:
            print(f"\nTask ID: {task['task_id']}")
            print(f"  Description: {task['description']}")
            print(f"  Agent: {task['agent']}")
            print(f"  Status: {task['status']}")
            print(f"  Priority: {task['priority']}")
            print(f"  Dependencies: {task.get('dependencies', [])}")
            if task.get('result'):
                print(f"  Result: {task['result']}")
        
        print("\n" + "="*60)
        
        return result
        
    except Exception as e:
        logger.error(f"Error running support system: {e}")
        raise


if __name__ == "__main__":
    config = load_config("config.yaml")
    
    # Example queries to test
    test_queries = [
        "Hey, I want to return my product.",
    ]
    
    # Run with first query
    run_support_system(config, test_queries[0])