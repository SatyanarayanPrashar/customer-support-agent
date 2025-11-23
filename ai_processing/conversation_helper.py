from typing import Dict, List
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.messages import BaseMessage

def convert_messages_to_dicts(msg: BaseMessage) -> Dict[str, str]:
    """
    Converts LangChain message objects into a list of dictionaries 
    compatible with standard LLM APIs (User, Assistant, Tool roles).
    """
    print(msg)
    formatted_mssg = {}

    if isinstance(msg, HumanMessage):
        formatted_mssg = {"role": "user", "content": msg.content}
    elif isinstance(msg, AIMessage):
        formatted_mssg = {"role": "assistant", "content": msg.content}
    elif isinstance(msg, ToolMessage):
        formatted_mssg = {
            "role": "tool", 
            "content": msg.content,
            "tool_call_id": msg.tool_call_id
        }
    elif isinstance(msg, SystemMessage):
        formatted_mssg.append({"role": "system", "content": msg.content})
            
    return formatted_mssg