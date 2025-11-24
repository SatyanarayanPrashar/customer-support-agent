from agents.billing.billing_agent import billing_agent
from agents.returns.return_agent import returns_agent
from agents.supervisor.supervisor_agent import supervisor_node
from agents.troubleshoot.troubleshoot_agent import troubleshoot_agent
from agents.warranty.warranty_agent import warranty_agent
from ai_processing.llm_client import LLM_Client
from ai_processing.states import AgentState
from langgraph.graph import StateGraph, END, START
from functools import partial

from utils.config_loader import load_config
from utils.logger import get_logger
logger = get_logger()
config = load_config("config.yaml")
llm_client = LLM_Client(config)

def route_to_human_input(state: AgentState) -> bool:
    """
    Determine if we need human input.
    """
    if state.get("needs_human_input", False):
        return "human_input"
    return "continue"
    
def route_from_supervisor(state: AgentState) -> str:
    """
    Called after the supervisor node.
    Decides whether to go to an agent, get human input, or finish.
    """
    
    # 1. Check if the supervisor *itself* needs human input
    if state.get("needs_human_input", False):
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
    # supervisor_node_with_client = partial(supervisor_node, llm_client=llm_client)
    # Initialize the graph
    workflow = StateGraph(AgentState)

    workflow.add_edge(START, "supervisor")
    workflow.add_node("supervisor", partial(supervisor_node, llm_client=llm_client))
    workflow.add_node("billing", partial(billing_agent, llm_client=llm_client))
    workflow.add_node("troubleshoot", troubleshoot_agent)
    workflow.add_node("warranty", warranty_agent)
    workflow.add_node("returns", returns_agent)
    
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "human_input": END,
            "troubleshoot": "troubleshoot",
            "billing": "billing",
            "warranty": "warranty",
            "returns": "returns",
            "finish": END
        }
    )
    
    agent_nodes = ["troubleshoot", "billing", "warranty", "returns"]
    for agent in agent_nodes:
        workflow.add_conditional_edges(
            agent,
            route_to_human_input,
            {
                "human_input": END,
                "continue": "supervisor"
            }
        )
    
    logger.info("Support graph created successfully.")
    return workflow.compile()