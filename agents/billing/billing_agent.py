import json
import re
from typing import Dict, List
from agents.billing._tools.billing_tools import get_bill_by_id, get_bills, refund_ticket, send_bill, tools
from agents.billing.compaction import _format_messages_to_string, compact_conversation_history
from agents.billing.prompt import BILLING_ANALYSIS_PROMPT
from ai_processing.states import AgentState, TaskStatus

from utils.logger import get_logger
logger = get_logger()

def billing_agent(state: "AgentState") -> "AgentState":
    """
    Billing agent that handles:
    - Viewing bills and charges
    - Processing refunds
    - Sending bills
    - Answering billing questions
    """
    
    llm_client = state.get("llm_client")
    current_task = state["current_task"]
    
    if not llm_client:
        logger.error("(billing agent) - LLM client not found in billing agent")
        mark_task_completed(state, current_task, "Error: LLM client not available")
        return state
    
    logger.info(f"(billing agent) - Current task: {current_task} recieved")

    try:
        analysis = analyze_billing_request(state, llm_client)
        action = analysis.get("action", "respond")
        message_to_user = analysis.get("message", "Processing...")
        
        if action == "need_info":
            state["needs_human_input"] = True
            state["human_input_prompt"] = message_to_user
            state["messages"].append({"role": "assistant", "content": message_to_user})
            current_task["status"] = TaskStatus.BLOCKED
            
        elif action == "respond" :
            # response = analysis.get("message", "I'm checking the issue, press 1 if you are still here")
            # state["messages"].append({"role": "assistant", "content": response})
            # state["needs_human_input"] = True
            # state["human_input_prompt"] = response
            # current_task["status"] = TaskStatus.BLOCKED
            state["needs_human_input"] = True
            state["human_input_prompt"] = message_to_user
            state["messages"].append({"role": "assistant", "content": message_to_user})
            current_task["status"] = TaskStatus.BLOCKED

        elif action == "completed":
            state["messages"].append({"role": "assistant", "content": message_to_user})
            mark_task_completed(state, current_task, message_to_user)
        
        else:
            state["messages"].append({"role": "assistant", "content": message_to_user})
            state["needs_human_input"] = True

    except Exception as e:
        logger.error(f"(billing agent) - error: {e}")
        error_msg = "I apologize, but I encountered an error accessing billing information. Could you please try again?"
        state["messages"].append({"role": "assistant", "content": error_msg})
        mark_task_completed(state, current_task, error_msg)
    
    return state

def analyze_billing_request(state, llm_client) -> Dict:
    """
    Analyze the billing request and determine what action to take
    """
    conversation = [
        {"role": "system", "content": BILLING_ANALYSIS_PROMPT},
        *state.get("messages")
    ]
    
    response = llm_client.invoke(input_list=conversation, tools=tools)

    tool_calls = [item for item in response.output if item.type == 'function_call']

    if tool_calls:
        logger.info(f"(billing agent) - {len(tool_calls)} Function calls detected.")

        for item in tool_calls:
            handle_use_tools(state, item, llm_client)

        return analyze_billing_request(state, llm_client)
    
    try:
        raw_text = response.output[0].content[0].text
    except (AttributeError, IndexError):
        logger.error("Could not extract text from LLM response")
        return {"error": "Empty response from LLM"}

    # Update state with the raw text
    clean_text = raw_text.strip()
    clean_text = re.sub(r"^```(?:json)?", "", clean_text)
    clean_text = re.sub(r"```$", "", clean_text)
    clean_text = clean_text.strip()

    try:
        return json.loads(clean_text)
    except json.JSONDecodeError:
        logger.warning(f"JSON parse failed, attempting repair on: {clean_text}")
        safe_response = re.sub(r"(?<!\\)'", '"', clean_text)
        safe_response = re.sub(r",\s*}", "}", safe_response)
        safe_response = re.sub(r",\s*]", "]", safe_response)
        try:
            return json.loads(safe_response)
        except json.JSONDecodeError:
            return {"error": "Failed to parse JSON", "raw_content": clean_text}

def handle_use_tools(state: dict, item, llm_client) -> dict:
    """
    Execute a single tool call from the ResponseFunctionToolCall object.
    """
    tool_name = item.name
    tool_call_id = item.call_id
    
    try:
        params = json.loads(item.arguments)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse arguments for {tool_name}: {item.arguments}")
        return {"tool": tool_name, "error": "Invalid JSON arguments"}

    tool_result_content = ""

    try:
        logger.info(f"(billing agent) - Executing tool: {tool_name} with params: {params}")

        if tool_name == "get_bills":
            tool_result_content = get_bills(params.get("ph_number"))
            
        elif tool_name == "get_bill_by_id":
            tool_result_content = get_bill_by_id(params.get("ph_number"), params.get("bill_id"))
            
        elif tool_name == "send_bill":
            tool_result_content = send_bill(params.get("ph_number"), params.get("bill_id"), params.get("mode"))
            
        elif tool_name == "refund_ticket":
            tool_result_content = refund_ticket(
                params.get("ph_number"), 
                params.get("bill_id"), 
                params.get("amount"), 
                params.get("reason")
            )
        else:
            logger.warning(f"(billing agent) - Unknown tool: {tool_name}")
            tool_result_content = f"Error: Unknown tool {tool_name}"

    except Exception as e:
        logger.error(f"(billing agent) - Error executing tool {tool_name}: {e}")
        tool_result_content = f"Error execution failed: {str(e)}"

    tool_msg = {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": str(tool_result_content)
    }
    
    state["messages"].append(tool_msg)
    
    return tool_msg

def mark_task_completed(state: "AgentState", task: Dict, result: str):
    """
    Mark the current task as completed
    """
    
    for t in state["subtasks"]:
        if t["task_id"] == task["task_id"]:
            t["status"] = "completed"
            t["result"] = result
            break
    
    state["current_task"] = None
