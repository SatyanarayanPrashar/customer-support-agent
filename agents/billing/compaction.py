from agents.billing.prompt import SUMMARY_PROMPT
from ai_processing.states import AgentState
from langchain_core.messages import HumanMessage

from utils.logger import get_logger
logger = get_logger()

def compact_conversation_history(state: "AgentState", llm_client) -> dict:
    """
    Checks message history length and, if too long,
    compacts it, returning a new message list for the state.
    """
    
    COMPACTION_THRESHOLD = 10 
    KEEP_LAST_N_MESSAGES = 4 
    
    messages = state.get("messages", [])

    # 1. If history is short, do nothing.
    if len(messages) <= COMPACTION_THRESHOLD:
        return {"messages": messages}

    messages_to_summarize = messages[:-KEEP_LAST_N_MESSAGES]
    messages_to_keep = messages[-KEEP_LAST_N_MESSAGES:]

    formatted_history = _format_messages_to_string(messages_to_summarize)

    prompt = [
        {"role": "system", "content": SUMMARY_PROMPT},
        {"role": "user", "content":  "conversation history to summarize: " + formatted_history}
    ]
    
    summary_text = llm_client.invoke(prompt) 
    new_message_list = [
        {"role": "system", "content": f"Summary of earlier conversation: {summary_text}"},
    ]

    new_message_list.extend(messages_to_keep)
    
    logger.info(f"--- Compaction complete. New message count: {len(new_message_list)} ---")

    return {"messages": new_message_list}

def _format_messages_to_string(messages: list) -> str:
    """Helper function to format a list of messages into a single string."""
    history_str = ""
    for msg in messages:
        if hasattr(msg, 'content'):
            role = "Customer" if isinstance(msg, HumanMessage) else "Agent"
            content = msg.content
        elif isinstance(msg, dict):
            role = msg.get("role", "unknown").capitalize()
            content = msg.get("content", "")
        else:
            continue
            
        history_str += f"{role}: {content}\n"
    return history_str