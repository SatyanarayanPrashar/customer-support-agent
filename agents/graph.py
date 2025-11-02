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

def route_to_human_input(state: AgentState) -> bool:
    """
    Determine if we need human input.
    """
    return state.get("needs_human_input", False)
    
def route_from_supervisor(state: AgentState) -> str:
    """
    Called after the supervisor node.
    Decides whether to go to an agent, get human input, or finish.
    """
    
    # 1. Check if the supervisor *itself* needs human input
    if state.get("needs_human_input", False):
        # Important: Clear the flag so it doesn't loop
        state["needs_human_input"] = False
        return "human_input"
    
    # 2. Route to a worker agent (based on supervisor's decision)
    next_agent = state.get("next_agent", "")
    if next_agent in ["troubleshoot", "billing", "warranty", "returns"]:
        return next_agent
    
    # 3. Default to finishing
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
    
    # 1. Supervisor's conditional edge
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "human_input": "human_input",
            "troubleshoot": "troubleshoot",
            "billing": "billing",
            "warranty": "warranty",
            "returns": "returns",
            "finish": END
        }
    )
    
    # 2. Worker agents' conditional edges
    agent_nodes = ["troubleshoot", "billing", "warranty", "returns"]
    for agent in agent_nodes:
        workflow.add_conditional_edges(
            agent,
            route_to_human_input,
            {
                True: "human_input",
                False: "supervisor"
            }
        )

    # 3. Human input always goes back to supervisor for re-evaluation
    workflow.add_edge("human_input", "supervisor")
    
    logger.info("Support graph created successfully.")
    return workflow.compile()
