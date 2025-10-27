import os
import sys
from PIL import Image
from io import BytesIO

from ai_processing.states import AgentState
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.graph import create_support_graph
from utils.config_loader import load_config
from utils.logger import get_logger

from langchain_core.messages import HumanMessage

logger = get_logger()
logger.info("✅ Logging initialized automatically")

config = load_config("config.yaml")
logger.info("using: %s", config['ai_processing']['model'])

def run_support_system():
    """
    Example usage of the multi-agent support system
    """
    
    # Create the graph
    graph = create_support_graph()

    png_bytes = graph.get_graph().draw_mermaid_png()
    img = Image.open(BytesIO(png_bytes))
    img.save("img/graph.png")
    
    # Initialize state with a complex query
    initial_state = AgentState(
        messages=[HumanMessage(content="Hey, my product is not working, also what is the warranty status?")],
        original_query="Hey, my product is not working, also what is the warranty status?",
        subtasks=[],
        current_task=None,
        next_agent="supervisor",
        needs_human_input=False,
        human_input_prompt=None,
        agent_context={},
        all_tasks_completed=False,
        final_response=None
    )
    
    # Run the graph
    logger.info("Starting multi-agent support system...")
    logger.info(f"User Query: {initial_state['original_query']}\n")
    
    # Execute the graph
    result = graph.invoke(initial_state)
    
    # logger.info conversation
    logger.info("=== Conversation Flow ===")
    for msg in result["messages"]:
        role = "User" if isinstance(msg, HumanMessage) else "Assistant"
        logger.info(f"{role}: {msg.content}\n")
    
    logger.info("=== Task Breakdown ===")
    for task in result["subtasks"]:
        logger.info(f"Task: {task['description']}")
        logger.info(f"  Agent: {task['agent']}")
        logger.info(f"  Status: {task['status']}")
        logger.info(f"  Result: {task.get('result', 'N/A')}\n")
    
    return result

if __name__ == "__main__":
    run_support_system()