import json
import re
from typing import Dict, List
from agents.billing._tools.billing_tools import get_bill_by_id, get_bills, refund_ticket, send_bill
from agents.billing.prompt import BILLING_ANALYSIS_PROMPT, BILLING_RESPONSE_PROMPT
from ai_processing.states import AgentState, AgentType, TaskStatus
from langchain_core.messages import HumanMessage, AIMessage

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
        state["messages"].append(
            AIMessage(content="I'm having trouble accessing the billing system. Please try again.")
        )
        mark_task_completed(state, current_task, "Error: LLM client not available")
        return state
    
    # Get conversation context
    conversation_history = get_conversation_summary(state)
    agent_context = state.get("agent_context", {})
    
    # Analyze what the customer needs
    try:
        analysis = analyze_billing_request(
            state["original_query"],
            conversation_history,
            agent_context,
            llm_client
        )
        
        logger.info(f"(billing agent) - Billing analysis: {analysis}")
        
        # Handle based on action
        if analysis["action"] == "need_info":
            state["needs_human_input"] = True
            response = analysis.get("message", "Could you please provide more details regarding your bill you are looking for like the phone number or the bill id?")
            state["human_input_prompt"] = response
            current_task["status"] = TaskStatus.BLOCKED

        elif analysis["action"] == "use_tools":
            # Execute tools and generate response
            response = handle_use_tools(analysis, state, llm_client)
            
        else:  # respond
            # Just respond to the customer
            response = analysis.get("message", "How else can I help with your billing?")
            mark_task_completed(state, current_task, response)
        
        # Add message and complete task
        state["messages"].append(AIMessage(content=response))
         
    except Exception as e:
        logger.error(f"(billing agent) - error: {e}")
        error_msg = "I apologize, but I encountered an error accessing billing information. Could you please try again?"
        state["messages"].append(AIMessage(content=error_msg))
        mark_task_completed(state, current_task, error_msg)
    
    return state

def analyze_billing_request(query: str, conversation_history: str, 
                            context: Dict, llm_client) -> Dict:
    """
    Analyze the billing request and determine what action to take
    """
    logger.info("(billing agent) - Analyzing billing request user query: " + query + "\ncontext: " + json.dumps(context))
    
    conversation = [
        {"role": "system", "content": BILLING_ANALYSIS_PROMPT},
        # {"role": "user", "content": query + "\ncontext: " + json.dumps(context)}
        {"role": "user", "content": conversation_history}
    ]
    
    response = llm_client.invoke(conversation)
    
    # Clean and parse JSON
    response = response.strip()

    # Remove code fences if present
    response = re.sub(r"^```(?:json)?", "", response)
    response = re.sub(r"```$", "", response)
    response = response.strip()

    # Try to fix single quotes and trailing commas
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        # Replace single quotes with double quotes safely
        safe_response = re.sub(r"(?<!\\)'", '"', response)
        safe_response = re.sub(r",\s*}", "}", safe_response)
        safe_response = re.sub(r",\s*]", "]", safe_response)
        return json.loads(safe_response)
    
    return json.loads(response)

def handle_use_tools(analysis: Dict, state: "AgentState", llm_client) -> str:
    """
    Execute the required tools and generate response
    """
    
    tools_to_call = analysis.get("tools_to_call", [])
    tool_results = []
    
    # Execute each tool
    for tool_call in tools_to_call:
        tool_name = tool_call["tool"]
        params = tool_call["params"]
        
        try:
            logger.info(f"(billing agent) - Executing tool: {tool_name} with params: {params}")
            
            if tool_name == "get_bills":
                result = get_bills(params["ph_number"])
                tool_results.append({"tool": tool_name, "result": result})
                
            elif tool_name == "get_bill_by_id":
                result = get_bill_by_id(params["ph_number"], params["bill_id"])
                tool_results.append({"tool": tool_name, "result": result})
                
            elif tool_name == "send_bill":
                result = send_bill(params["ph_number"], params["bill_id"], params["mode"])
                tool_results.append({"tool": tool_name, "result": result})
                
            elif tool_name == "refund_ticket":
                result = refund_ticket(
                    params["ph_number"],
                    params["bill_id"],
                    params["amount"],
                    params["reason"]
                )
                tool_results.append({"tool": tool_name, "result": result})
            
            else:
                logger.warning(f"(billing agent) - Unknown tool: {tool_name}")
                
        except Exception as e:
            logger.error(f"(billing agent) - Error executing tool {tool_name}: {e}")
            tool_results.append({
                "tool": tool_name,
                "result": f"Error: {str(e)}"
            })
    
    # Store tool results in context for other agents
    state["agent_context"]["billing_tool_results"] = tool_results
    
    # Generate response based on tool results
    response = generate_billing_response(
        state["original_query"],
        tool_results,
        state.get("agent_context", {}),
        llm_client
    )
    
    return response

def generate_billing_response(query: str, tool_results: List[Dict], 
                              context: Dict, llm_client) -> str:
    """
    Generate a natural response based on tool execution results
    """
    
    conversation = [
        {"role": "system", "content": "You are a helpful billing support agent."},
        {"role": "user", "content": BILLING_RESPONSE_PROMPT.format(
            query=query,
            tool_results=json.dumps(tool_results, indent=2),
            context=json.dumps(context)
        )}
    ]
    
    response = llm_client.invoke(conversation)
    return response.strip()

def get_conversation_summary(state: "AgentState") -> str:
    """
    Get a summary of the conversation history
    """
    
    messages = state.get("messages", [])
    if not messages:
        return "No prior conversation"
    
    # Get last 4 messages for context
    recent_messages = messages[-4:]
    summary_parts = []
    
    for msg in recent_messages:
        role = "Customer" if isinstance(msg, HumanMessage) else "Agent"
        summary_parts.append(f"{role}: {msg.content}")
    
    return "\n".join(summary_parts)

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
