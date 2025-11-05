from ai_processing.states import AgentState, AgentType, TaskStatus
from langchain_core.messages import HumanMessage, AIMessage
from utils.logger import get_logger

logger = get_logger()

def human_input_node(state: AgentState) -> AgentState:
    """
    Handle human input requests.
    This is where the graph pauses and waits for user input.
    """
    
    if state.get("human_input_prompt"):
        state["messages"].append(AIMessage(content=state["human_input_prompt"]))
    
    user_input = input("\n--------------------------------------------------------------------------------\nAssistant: " + state.get("human_input_prompt", "Please provide the required information: ") + "\nYou:")
    print("--------------------------------------------------------------------------------")
    state["messages"].append(HumanMessage(content=user_input))

    state["needs_human_input"] = False
    state["human_input_prompt"] = None
    state["current_task"]["status"] = TaskStatus.IN_PROGRESS

    return state