import json
from agents.supervisor.prompt import SUPERVISOR_DECOMPOSITION_PROMPT, SUPERVISOR_ROUTING_PROMPT, FINAL_RESPONSE_PROMPT, TURN_4_PROMPT, TURN_3_PROMPT, GENERATE_WELCOME, GENERATE_HELPFUL
from ai_processing.get_response import Get_response
from ai_processing.states import AgentState, SubTask, TaskStatus
from langchain_core.messages import AIMessage
from typing import List, Optional

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
        logger.error("(supervisor) - LLM client not found in state")
        state["all_tasks_completed"] = True
        state["next_agent"] = "finish"
        state["final_response"] = "Error: System not properly configured."
        return state
    
    
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
            {"role": "system", "content": SUPERVISOR_DECOMPOSITION_PROMPT},
            {"role": "user", "content": "Here is the customer Query: " + query}
        ]
        
        # Get LLM response
        response = llm_client.invoke(conversation)
        
        # Clean response - remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        data = json.loads(response)
        
        # Case 1: LLM returned an unactionable message (dict with 'response' key)
        if isinstance(data, dict) and "response" in data:
            logger.info("(supervisor) - LLM detected casual/unactionable query")
            unactionable_message = data["response"]
            return ([], unactionable_message)
        
        # Case 2: LLM returned empty array (casual conversation)
        if isinstance(data, list) and len(data) == 0:
            logger.info("(supervisor) - Empty task list")
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
            
            logger.info(f"(supervisor) - Generated {len(subtasks)} actionable subtasks")
            return (subtasks, None)
        
        # Unexpected JSON format
        logger.error(f"Unexpected JSON format from LLM: {type(data)}")
        return ([], None)
        
    except json.JSONDecodeError as e:
        logger.error(f"(supervisor) - Failed to parse LLM response as JSON: {e}")
        logger.error(f"(supervisor) - Response was: {response}")
        return ([], None)
    except Exception as e:
        logger.error(f"(supervisor) - Error in decompose_query_with_llm: {e}")
        return ([], None)
