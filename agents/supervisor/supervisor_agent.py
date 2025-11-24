import json
from agents.supervisor.prompt import SUPERVISOR_DECOMPOSITION_PROMPT
from ai_processing.llm_client import LLM_Client
from ai_processing.states import AgentState, SubTask, TaskStatus
from typing import List, Optional

from utils.logger import get_logger
logger = get_logger()

def supervisor_node(state: AgentState, llm_client: LLM_Client) -> AgentState:
    """
    The supervisor agent that:
    1. Analyzes the user query using LLM
    2. Decomposes it into subtasks (or handles casual conversation)
    3. Determines task dependencies and order
    4. Routes to the next available agent
    5. Manages casual conversation turns
    """
    
    if not llm_client:
        logger.error("(supervisor) - LLM client not found in state")
        state["all_tasks_completed"] = True
        state["next_agent"] = "finish"
        return state

    if "casual_turn_count" not in state:
        state["casual_turn_count"] = 0
    if "awaiting_real_query" not in state:
        state["awaiting_real_query"] = False
    
    # first time supervisor is called
    if not state.get("subtasks"):
        logger.info("(supervisor) - Analyzing user query")
        
        subtasks, unactionable_msg = decompose_query_with_llm(state, llm_client)
        
        # If no tasks (casual conversation), handle it
        if not subtasks:
            logger.info("(supervisor) - Casual conversation detected, no tasks created")
            state["casual_turn_count"] += 1
            
            response = "I'm sorry, I didn't quite catch that. How can I help you today?"

            if unactionable_msg:
                response = unactionable_msg
            
            state["messages"].append({"role": "assistant", "content":response})
            state["all_tasks_completed"] = True
            state["next_agent"] = "human_input"
            state["awaiting_real_query"] = True
            return state
        
        state["casual_turn_count"] = 0
        state["awaiting_real_query"] = False
        state["subtasks"] = subtasks
        logger.info(f"(supervisor) - Updated state with {len(subtasks)} subtasks")

    else:
        logger.info("(supervisor) - Continuing with existing subtasks")

    next_task = get_next_task(state["subtasks"])
    logger.info(f"(supervisor) - Next task: {next_task}")
    
    if next_task is None:
        all_completed = all(t["status"] == TaskStatus.COMPLETED for t in state["subtasks"])
        any_in_progress = any(t["status"] == TaskStatus.IN_PROGRESS for t in state["subtasks"])

        if all_completed:
            logger.info("(supervisor) - All tasks completed")
            state["all_tasks_completed"] = True
            state["next_agent"] = "finish"
        elif any_in_progress:
            logger.info("(supervisor) - Tasks in progress; waiting for agent response")
            state["next_agent"] = state["current_task"]["agent"]
        else:
            logger.info("(supervisor) - No available tasks, but not all completed (possible dependency wait)")
            state["next_agent"] = None

    else:
        for task in state["subtasks"]:
            if task["task_id"] == next_task["task_id"]:
                task["status"] = TaskStatus.IN_PROGRESS
        
        state["current_task"] = next_task
        state["next_agent"] = next_task["agent"]
        
        logger.info(f"(supervisor) - Routing to {next_task['agent']} for: {next_task['description']}")
    
    return state

def decompose_query_with_llm(state, llm_client: LLM_Client) -> tuple[List[SubTask], Optional[str]]:
    """
    Use LLM to decompose the user query into subtasks.
    Returns (subtasks_list, unactionable_message).
    
    - If query is actionable: returns ([subtasks], None)
    - If query is casual/unactionable: returns ([], "LLM generated message")
    """
    conversation = [
        {"role": "system", "content": SUPERVISOR_DECOMPOSITION_PROMPT},
        *state.get("messages")
    ]
    
    try:
        
        response = llm_client.invoke(conversation)
        response = response.output[0].content[0].text
        
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()
        
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            logger.info("(supervisor) - Response is not JSON, treating as casual message")
            return ([], response)
        
        # Case 1: LLM returned an unactionable message
        if isinstance(data, str):
            logger.info("(supervisor) - LLM detected casual/unactionable query")
            unactionable_message = data
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


def get_next_task(subtasks: List[SubTask]) -> Optional[SubTask]:
    """
    Get the next task that should be executed based on:
    1. Dependencies (all dependent tasks must be completed)
    2. Priority (lower number = higher priority)
    3. Status (only pending tasks)
    """
    
    available_tasks = []
    logger.info(f"(supervisor) - Checking {len(subtasks)} subtasks for next task, task: {subtasks}")
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
