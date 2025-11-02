import os
import sys
from typing import Any, Dict
from langchain_core.messages import HumanMessage, AIMessage

from ai_processing.get_response import Get_response
from ai_processing.states import AgentState
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.graph import create_support_graph
from utils.config_loader import load_config
from utils.logger import get_logger

from langchain_core.messages import HumanMessage

logger = get_logger()
config = load_config("config.yaml")
logger.info("using: %s", config['ai_processing']['model'])

if __name__ == "__main__":
    graph = create_support_graph()
    mermaid_png = graph.get_graph().draw_mermaid_png()
    with open("support_graph.png", "wb") as f:
        f.write(mermaid_png)