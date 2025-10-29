from agents.billing.billing_agent import billing_agent
from agents.returns.return_agent import returns_agent
from agents.supervisor.supervisor_agent import supervisor_node
from agents.troubleshoot.troubleshoot_agent import troubleshoot_agent
from agents.warranty.warranty_agent import warranty_agent
from ai_processing.states import AgentState, AgentType
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, END, START

from utils.logger import get_logger
logger = get_logger()

def human_input_node(state: AgentState) -> AgentState:
    """
    Handle human input requests.
    This is where the graph pauses and waits for user input.
    """
    
    if state.get("human_input_prompt"):
        state["messages"].append(AIMessage(content=state["human_input_prompt"]))
    
    # The graph will interrupt here for human input
    # When resumed, the user's response will be in the latest message
    
    return state

def route_to_agent(state: AgentState) -> str:
    """
    Determine which node to go to next based on state.
    Only called from supervisor node.
    """
    
    # Route based on next_agent
    next_agent = state.get("next_agent", "")
    
    if next_agent == "finish" or state.get("all_tasks_completed"):
        return "finish"
    
    if next_agent in ["troubleshoot", "billing", "warranty", "returns"]:
        return next_agent
    
    # Default to end if no valid routing
    return "finish"

def create_support_graph():
    """
    Create the LangGraph workflow for the multi-agent system
    """
    
    # Initialize the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_edge(START, "supervisor")
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("troubleshoot", troubleshoot_agent)
    workflow.add_node("billing", billing_agent)
    workflow.add_node("warranty", warranty_agent)
    workflow.add_node("returns", returns_agent)
    workflow.add_node("human_input", human_input_node)
    
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
    
    logger.info("Support graph created successfully.")
    return workflow.compile()
