import json
from agents.supervisor.prompt import SUPERVISOR_DECOMPOSITION_PROMPT, SUPERVISOR_ROUTING_PROMPT, FINAL_RESPONSE_PROMPT, TURN_4_PROMPT, TURN_3_PROMPT, GENERATE_WELCOME, GENERATE_HELPFUL
from ai_processing.get_response import Get_response
from ai_processing.states import AgentState, AgentType, SubTask, TaskStatus
from langchain_core.messages import AIMessage
from typing import Any, Dict, List, Optional

from utils.logger import get_logger
logger = get_logger()

def supervisor_node(state: AgentState) -> AgentState:
    """
    The supervisor agent that:
    1. Analyzes the user query using LLM
    2. Decomposes it into subtasks (or handles casual conversation)
    3. Determines task dependencies and order
    4. Routes to the next available agent
    5. Manages casual conversation turns
    """
    
    llm_client = state.get("llm_client")
    
    if not llm_client:
        logger.error("LLM client not found in state")
        state["all_tasks_completed"] = True
        state["next_agent"] = "finish"
        state["final_response"] = "Error: System not properly configured."
        return state
    
    # Initialize casual turn tracking if not present
    if "casual_turn_count" not in state:
        state["casual_turn_count"] = 0
    if "awaiting_real_query" not in state:
        state["awaiting_real_query"] = False
    
    # If this is the first time supervisor is called
    if not state.get("subtasks"):
        logger.info("Analyzing user query")
        
        # Decompose the query into subtasks using LLM
        # This returns (subtasks_list, unactionable_message)
        subtasks, unactionable_msg = decompose_query_with_llm(state["original_query"], llm_client)
        logger.info("unpacked")
        
        # If no tasks (casual conversation), handle it
        if not subtasks:
            logger.info("Casual conversation detected, no tasks created")
            state["casual_turn_count"] += 1
            
            # Use the LLM-generated unactionable message if available
            if unactionable_msg:
                response = unactionable_msg
            else:
                # Generate response based on turn count (fallback)
                if state["casual_turn_count"] == 1:
                    logger.info("generating welcome")
                    response = generate_welcome_with_capabilities(llm_client)
                elif state["casual_turn_count"] == 2:
                    logger.info("generating helpful")
                    response = generate_helpful_prompt(llm_client)
                elif state["casual_turn_count"] >= 3:
                    logger.info("generating final")
                    response = generate_final_prompt(state["casual_turn_count"], llm_client)
            
            state["messages"].append(AIMessage(content=response))
            state["all_tasks_completed"] = True
            state["next_agent"] = "human_input"
            state["final_response"] = response
            state["awaiting_real_query"] = True
            return state
        
        # Real tasks detected - reset casual counters
        state["casual_turn_count"] = 0
        state["awaiting_real_query"] = False
        state["subtasks"] = subtasks
        logger.info(f"Generated {len(subtasks)} subtasks")
    
    # Find the next task to execute
    next_task = get_next_task(state["subtasks"])
    
    if next_task is None:
        # All tasks completed
        logger.info("All tasks completed")
        state["all_tasks_completed"] = True
        state["next_agent"] = "finish"
        state["final_response"] = compile_final_response_with_llm(state, llm_client)
    else:
        # Update task status
        for task in state["subtasks"]:
            if task["task_id"] == next_task["task_id"]:
                task["status"] = TaskStatus.IN_PROGRESS
        
        state["current_task"] = next_task
        state["next_agent"] = next_task["agent"]
        
        # Generate routing message using LLM
        routing_message = generate_routing_message(state, llm_client)
        
        # Add supervisor message explaining what we're doing
        state["messages"].append(AIMessage(content=routing_message))
        
        logger.info(f"Routing to {next_task['agent']} for: {next_task['description']}")
    
    return state

def decompose_query_with_llm(query: str, llm_client: Get_response) -> tuple[List[SubTask], Optional[str]]:
    """
    Use LLM to decompose the user query into subtasks.
    Returns (subtasks_list, unactionable_message).
    
    - If query is actionable: returns ([subtasks], None)
    - If query is casual/unactionable: returns ([], "LLM generated message")
    """
    
    try:
        # Prepare the conversation for LLM
        conversation = [
            {"role": "system", "content": "You are an expert at analyzing customer support queries and breaking them into actionable tasks."},
            {"role": "user", "content": SUPERVISOR_DECOMPOSITION_PROMPT.format(query=query)}
        ]
        
        # Get LLM response
        response = llm_client.invoke(conversation)
        logger.debug(f"LLM decomposition response: {response}")
        
        # Clean response - remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        # Parse JSON response
        data = json.loads(response)
        
        # Case 1: LLM returned an unactionable message (dict with 'response' key)
        if isinstance(data, dict) and "response" in data:
            logger.info("LLM detected casual/unactionable query")
            unactionable_message = data["response"]
            return ([], unactionable_message)
        
        # Case 2: LLM returned empty array (casual conversation)
        if isinstance(data, list) and len(data) == 0:
            logger.info("Empty task list - casual conversation")
            return ([], None)
        
        # Case 3: LLM returned actionable subtasks (list with items)
        if isinstance(data, list):
            subtasks = []
            for task_data in data:
                subtask = SubTask(
                    task_id=task_data["task_id"],
                    description=task_data["description"],
                    agent=task_data["agent"],
                    status=TaskStatus.PENDING,
                    result=None,
                    dependencies=task_data.get("dependencies", []),
                    priority=task_data.get("priority", 1)
                )
                subtasks.append(subtask)
            
            logger.info(f"Generated {len(subtasks)} actionable subtasks")
            return (subtasks, None)
        
        # Unexpected JSON format
        logger.error(f"Unexpected JSON format from LLM: {type(data)}")
        return ([], None)
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        logger.error(f"Response was: {response}")
        return ([], None)
    except Exception as e:
        logger.error(f"Error in decompose_query_with_llm: {e}")
        return ([], None)

def generate_routing_message(state: AgentState, llm_client: Get_response) -> str:
    """
    Generate a natural message explaining what the supervisor is doing next.
    """
    
    try:
        completed_tasks = [t for t in state["subtasks"] if t["status"] == TaskStatus.COMPLETED]
        pending_tasks = [t for t in state["subtasks"] if t["status"] == TaskStatus.PENDING]
        
        completed_desc = [t["description"] for t in completed_tasks]
        pending_desc = [t["description"] for t in pending_tasks]
        
        conversation = [
            {"role": "system", "content": "You are a friendly customer support supervisor."},
            {"role": "user", "content": SUPERVISOR_ROUTING_PROMPT.format(
                completed_tasks=completed_desc,
                pending_tasks=pending_desc,
                agent_context=state.get("agent_context", {})
            )}
        ]
        
        response = llm_client.invoke(conversation)
        return response.strip()
        
    except Exception as e:
        logger.error(f"Error generating routing message: {e}")
        # Fallback to simple message
        return f"Let me {state['current_task']['description']}."

def compile_final_response_with_llm(state: AgentState, llm_client: Get_response) -> str:
    """
    Compile results from all agents into a final response using LLM.
    """
    
    try:
        completed_tasks = [t for t in state["subtasks"] if t["status"] == TaskStatus.COMPLETED]
        
        task_summaries = []
        for task in completed_tasks:
            task_summaries.append(f"- {task['description']}: {task['result']}")
        
        prompt = FINAL_RESPONSE_PROMPT
        
        conversation = [
            {"role": "system", "content": "You are a helpful customer support agent."},
            {"role": "user", "content": prompt}
        ]
        
        response = llm_client.invoke(conversation)
        return response.strip()
        
    except Exception as e:
        logger.error(f"Error compiling final response: {e}")
        # Fallback response
        return "I've addressed your concerns. Is there anything else I can help you with?"

def get_next_task(subtasks: List[SubTask]) -> Optional[SubTask]:
    """
    Get the next task that should be executed based on:
    1. Dependencies (all dependent tasks must be completed)
    2. Priority (lower number = higher priority)
    3. Status (only pending tasks)
    """
    
    available_tasks = []
    
    for task in subtasks:
        # Skip if not pending
        if task["status"] != TaskStatus.PENDING:
            continue
        
        # Check if all dependencies are completed
        dependencies_met = True
        for dep_id in task["dependencies"]:
            dep_task = next((t for t in subtasks if t["task_id"] == dep_id), None)
            if dep_task and dep_task["status"] != TaskStatus.COMPLETED:
                dependencies_met = False
                break
        
        if dependencies_met:
            available_tasks.append(task)
    
    # Sort by priority and return the highest priority task
    if available_tasks:
        return sorted(available_tasks, key=lambda x: x["priority"])[0]
    
    return None

def generate_welcome_with_capabilities(llm_client: Get_response) -> str:
    """
    Generate a welcoming response that showcases system capabilities.
    Used on first casual interaction.
    """
    
    try:
        prompt = GENERATE_WELCOME
        
        conversation = [
            {"role": "system", "content": "You are a friendly customer support agent introducing your capabilities."},
            {"role": "user", "content": prompt}
        ]
        
        response = llm_client.invoke(conversation)
        return response.strip()
        
    except Exception as e:
        logger.error(f"Error generating welcome: {e}")
        return "Hello! I can help you with product troubleshooting, billing questions, warranty information, returns, and account management. What do you need help with today?"

def generate_helpful_prompt(llm_client: Get_response) -> str:
    """
    Generate a more specific prompt for the second casual turn.
    """
    
    try:
        prompt = GENERATE_HELPFUL
        
        conversation = [
            {"role": "system", "content": "You are a friendly customer support agent."},
            {"role": "user", "content": prompt}
        ]
        
        response = llm_client.invoke(conversation)
        return response.strip()
        
    except Exception as e:
        logger.error(f"Error generating helpful prompt: {e}")
        return "I'm here to help! For example, I can troubleshoot issues, check warranty status, or answer billing questions. What would you like to know?"

def generate_final_prompt(turn_count: int, llm_client: Get_response) -> str:
    """
    Generate a more direct prompt after multiple casual turns.
    After 3+ turns without a real question, be more explicit.
    """
    
    try:
        if turn_count >= 4:
            # After 4+ turns, suggest they come back later
            prompt = TURN_4_PROMPT
        else:
            # Turn 3 - be direct but helpful
            prompt = TURN_3_PROMPT
        
        conversation = [
            {"role": "system", "content": "You are a friendly but direct customer support agent."},
            {"role": "user", "content": prompt}
        ]
        
        response = llm_client.invoke(conversation)
        return response.strip()
        
    except Exception as e:
        logger.error(f"Error generating final prompt: {e}")
        if turn_count >= 4:
            return "It looks like you might not need assistance right now. Feel free to reach out whenever you have a question!"
        else:
            return "I'd love to help! Could you let me know what specific issue you're experiencing?"
