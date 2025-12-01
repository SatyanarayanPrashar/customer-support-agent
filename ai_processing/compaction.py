from typing import TypedDict, List, Dict, Union, Any

from utils.logger import get_logger
logger = get_logger()

def compact_history(msg_list, llm_client, full_compaction: bool = False) -> dict:
    """
    Checks message history length and, if too long,
    compacts it, returning a new message list for the state.
    """
    
    KEEP_LAST_N = 3    
   
    if full_compaction:
        messages_to_summarize = msg_list[:]
        messages_to_keep = []
        logger.info(f"--- Performing FULL compaction on {len(msg_list)} messages ---")
    else:
        messages_to_summarize = msg_list[:-KEEP_LAST_N]
        messages_to_keep = msg_list[-KEEP_LAST_N:]
        logger.info(f"--- Compacting oldest {len(messages_to_summarize)} messages, keeping last {len(messages_to_keep)} ---")
    
    history_text = _format_dict_messages(messages_to_summarize)

    prompt = [
        {"role": "system", "content": """You have to summarise the conversation between an Customer support AI Agent and the customer.
RULES:
1. Be concise but donot leave any information which can be helpful for the agent to resolve user's querry
2. Responed only the summary without any extra comment or message.

Example Response:
"Because of calculation mistake, user was charged more. User's ph no. 1245667890 and bil id is B002."""},
        {"role": "user", "content":  "conversation history to summarize: " + history_text}
    ]
    
    response = llm_client.invoke(prompt) 
    summary_text = response.output[0].content[0].text
    new_message_list = [
        {"role": "developer", "content": f"Summary of earlier conversation: {summary_text}"},
    ]

    new_message_list.extend(messages_to_keep)
    
    logger.info(f"--- Compaction complete. New message count: {len(new_message_list)} ---")

    return new_message_list

def _format_dict_messages(messages: List[Dict[str, str]]) -> str:
    """
    Converts a list of dict messages into a readable string for the LLM.
    """
    formatted_str = ""
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        formatted_str += f"{role}: {content}\n"
    return formatted_str
