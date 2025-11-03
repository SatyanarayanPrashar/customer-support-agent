import json
from agents.supervisor.prompt import (
    SUPERVISOR_DECOMPOSITION_PROMPT,
    FINAL_RESPONSE_PROMPT,
    GENERATE_HELPFUL,
)
from ai_processing.get_response import Get_response
from ai_processing.states import AgentState, SubTask, TaskStatus
from langchain_core.messages import AIMessage, HumanMessage
from typing import List, Optional, Tuple

from utils.logger import get_logger

logger = get_logger()


def supervisor_node(state: AgentState) -> AgentState:
    """
    The supervisor agent that:
    1. Analyzes the user query using LLM
    2. Decomposes it into subtasks (or handles casual conversation)
    3. Determines task dependencies and order
    4. Routes to the next available agent or human input
    5. Manages conversation flow and human-in-the-loop requirements
    
    State Flow:
    - New conversation → Analyze query → Generate subtasks or casual response
    - Resumed conversation with human input → Process input → Route accordingly
    - All tasks completed → Generate final response → End
    """
    
    # Validate LLM client
    llm_client = state.get("llm_client")
    if not llm_client:
        logger.error("(supervisor) - LLM client not found in state")
        state["all_tasks_completed"] = True
        state["next_agent"] = ""
        state["final_response"] = "Error: System not properly configured. LLM client missing."
        return state
    
    # Validate messages exist
    if not state.get("messages"):
        logger.error("(supervisor) - No messages in state")
        state["all_tasks_completed"] = True
        state["final_response"] = "Error: No messages found."
        return state
    
    # Get the latest user message
    latest_message = state["messages"][-1]
    if not isinstance(latest_message, HumanMessage):
        logger.warning("(supervisor) - Latest message is not from user, waiting for user input")
        return state
    
    current_query = latest_message.content
    logger.info(f"(supervisor) - Processing query: {current_query[:50]}...")
    
    # Check if this is a new conversation or a resumption
    is_new_conversation = len(state.get("subtasks", [])) == 0
    
    if is_new_conversation:
        logger.info("(supervisor) - New conversation detected")
        return handle_new_conversation(state, current_query, llm_client)
    else:
        logger.info("(supervisor) - Resuming existing conversation")
        return handle_resumed_conversation(state, current_query, llm_client)


def handle_new_conversation(state: AgentState, query: str, llm_client: Get_response) -> AgentState:
    """
    Handle a brand new conversation.
    Decompose the query into subtasks or recognize it as casual conversation.
    """
    
    logger.info("(supervisor) - Handling new conversation")
    
    # Decompose the query
    subtasks, unactionable_message = decompose_query_with_llm(query, llm_client)
    
    # Case 1: Query is unactionable or casual
    if unactionable_message or len(subtasks) == 0:
        logger.info("(supervisor) - Query is casual/unactionable")
        
        # Generate a helpful response for casual query
        response_message = unactionable_message or generate_casual_response(query, llm_client)
        
        state["messages"].append(AIMessage(content=response_message))
        state["final_response"] = response_message
        state["all_tasks_completed"] = True
        state["next_agent"] = ""
        
        logger.info("(supervisor) - Casual response generated, conversation complete")
        return state
    
    # Case 2: Query is actionable and decomposed into subtasks
    logger.info(f"(supervisor) - Generated {len(subtasks)} subtasks")
    state["subtasks"] = subtasks
    
    # Sort subtasks by priority and dependencies
    sorted_tasks = sort_tasks_by_dependencies(subtasks)
    state["subtasks"] = sorted_tasks
    
    # Get the first available task (highest priority, no unmet dependencies)
    current_task = get_next_available_task(state)
    
    if not current_task:
        logger.error("(supervisor) - No available task to start")
        state["final_response"] = "Error: Unable to determine next action."
        state["all_tasks_completed"] = True
        return state
    
    state["current_task"] = current_task
    
    # Route to the appropriate agent
    agent_name = current_task["agent"].lower()
    state["next_agent"] = agent_name
    
    logger.info(f"(supervisor) - Routing to agent: {agent_name}")
    logger.info(f"(supervisor) - Current task: {current_task['task_id']} - {current_task['description']}")
    
    return state


def handle_resumed_conversation(state: AgentState, query: str, llm_client: Get_response) -> AgentState:
    """
    Handle a resumed conversation.
    Process the human input and determine next steps.
    """
    
    logger.info("(supervisor) - Handling resumed conversation")
    
    current_task = state.get("current_task")
    all_tasks = state.get("subtasks", [])
    
    # Validate state consistency
    if not current_task:
        logger.warning("(supervisor) - No current task in resumed conversation")
        state["final_response"] = "Error: Task state inconsistent."
        state["all_tasks_completed"] = True
        return state
    
    # Update current task status based on human input
    # The human input should have been processed by the worker agent
    # Here we check if the human input resolves any blocking tasks
    
    logger.info(f"(supervisor) - Human input processed: {query[:100]}...")
    
    # Mark current task as potentially resolved if it was blocked
    current_task_idx = next(
        (i for i, t in enumerate(all_tasks) if t["task_id"] == current_task["task_id"]),
        None
    )
    
    if current_task_idx is not None:
        # The worker agent should have updated the task status
        # We just retrieve the latest status
        all_tasks[current_task_idx] = current_task
    
    state["subtasks"] = all_tasks
    
    # Check if all tasks are completed
    if all(task["status"] in [TaskStatus.COMPLETED, TaskStatus.FAILED] for task in all_tasks):
        logger.info("(supervisor) - All tasks completed")
        state["all_tasks_completed"] = True
        
        # Generate final response
        final_response = generate_final_response(state, llm_client)
        state["messages"].append(AIMessage(content=final_response))
        state["final_response"] = final_response
        state["next_agent"] = ""
        
        return state
    
    # Get the next available task
    current_task = get_next_available_task(state)
    
    if not current_task:
        logger.info("(supervisor) - No more available tasks, generating final response")
        state["all_tasks_completed"] = True
        
        final_response = generate_final_response(state, llm_client)
        state["messages"].append(AIMessage(content=final_response))
        state["final_response"] = final_response
        state["next_agent"] = ""
        
        return state
    
    # Route to next agent
    state["current_task"] = current_task
    agent_name = current_task["agent"].lower()
    state["next_agent"] = agent_name
    
    logger.info(f"(supervisor) - Routing to next agent: {agent_name}")
    logger.info(f"(supervisor) - Current task: {current_task['task_id']} - {current_task['description']}")
    
    return state


def decompose_query_with_llm(query: str, llm_client: Get_response) -> Tuple[List[SubTask], Optional[str]]:
    """
    Use LLM to decompose the user query into subtasks.
    
    Returns:
        (subtasks_list, unactionable_message)
        - If query is actionable: returns ([subtasks], None)
        - If query is casual/unactionable: returns ([], "LLM generated message")
    """
    
    try:
        logger.info("(supervisor) - Decomposing query with LLM")
        
        # Prepare the conversation for LLM
        conversation = [
            {"role": "system", "content": SUPERVISOR_DECOMPOSITION_PROMPT},
            {"role": "user", "content": f"Here is the customer Query: {query}"}
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
        
        logger.debug(f"(supervisor) - LLM raw response: {response[:200]}...")
        
        data = json.loads(response)
        
        # Case 1: LLM returned an unactionable response (dict with 'response' key)
        if isinstance(data, dict) and "response" in data:
            logger.info("(supervisor) - Query marked as unactionable by LLM")
            unactionable_message = data["response"]
            return ([], unactionable_message)
        
        # Case 2: LLM returned empty array
        if isinstance(data, list) and len(data) == 0:
            logger.info("(supervisor) - Empty task list returned")
            return ([], None)
        
        # Case 3: LLM returned actionable subtasks (list with items)
        if isinstance(data, list):
            subtasks = []
            for idx, task_data in enumerate(data):
                try:
                    subtask = SubTask(
                        task_id=task_data.get("task_id", f"task_{idx}"),
                        description=task_data.get("description", ""),
                        agent=task_data.get("agent", "supervisor"),
                        status=TaskStatus.PENDING,
                        result=None,
                        dependencies=task_data.get("dependencies", []),
                        priority=task_data.get("priority", idx)
                    )
                    subtasks.append(subtask)
                    logger.debug(f"(supervisor) - Created subtask: {subtask['task_id']}")
                except Exception as e:
                    logger.error(f"(supervisor) - Error creating subtask from data {task_data}: {e}")
                    continue
            
            logger.info(f"(supervisor) - Successfully created {len(subtasks)} subtasks")
            return (subtasks, None)
        
        # Unexpected JSON format
        logger.error(f"(supervisor) - Unexpected JSON format from LLM: {type(data)}")
        return ([], None)
        
    except json.JSONDecodeError as e:
        logger.error(f"(supervisor) - Failed to parse LLM response as JSON: {e}")
        logger.debug(f"(supervisor) - Response was: {response}")
        return ([], None)
    except Exception as e:
        logger.error(f"(supervisor) - Error in decompose_query_with_llm: {e}", exc_info=True)
        return ([], None)


def sort_tasks_by_dependencies(tasks: List[SubTask]) -> List[SubTask]:
    """
    Sort tasks by dependencies and priority.
    Tasks with no dependencies come first, then their dependents.
    """
    
    try:
        logger.info(f"(supervisor) - Sorting {len(tasks)} tasks by dependencies")
        
        sorted_tasks = []
        remaining_tasks = {task["task_id"]: task for task in tasks}
        completed_task_ids = set()
        
        while remaining_tasks:
            # Find tasks with all dependencies satisfied
            available_tasks = [
                task for task_id, task in remaining_tasks.items()
                if all(dep in completed_task_ids for dep in task.get("dependencies", []))
            ]
            
            if not available_tasks:
                # Circular dependency or missing task
                logger.warning("(supervisor) - Possible circular dependency detected")
                # Add remaining tasks as-is
                sorted_tasks.extend(remaining_tasks.values())
                break
            
            # Sort by priority
            available_tasks.sort(key=lambda t: t.get("priority", 0))
            
            for task in available_tasks:
                sorted_tasks.append(task)
                completed_task_ids.add(task["task_id"])
                del remaining_tasks[task["task_id"]]
        
        logger.info(f"(supervisor) - Tasks sorted successfully")
        return sorted_tasks
    
    except Exception as e:
        logger.error(f"(supervisor) - Error sorting tasks: {e}")
        return tasks


def get_next_available_task(state: AgentState) -> Optional[SubTask]:
    """
    Get the next available task to process.
    A task is available if:
    1. Its status is PENDING
    2. All its dependencies are COMPLETED or BLOCKED (resolved by human)
    """
    
    subtasks = state.get("subtasks", [])
    
    for task in subtasks:
        # Task must be pending
        if task["status"] != TaskStatus.PENDING:
            continue
        
        # Check if all dependencies are satisfied
        dependencies_satisfied = True
        for dep_id in task.get("dependencies", []):
            dep_task = next((t for t in subtasks if t["task_id"] == dep_id), None)
            if dep_task and dep_task["status"] not in [TaskStatus.COMPLETED, TaskStatus.BLOCKED]:
                dependencies_satisfied = False
                break
        
        if dependencies_satisfied:
            logger.info(f"(supervisor) - Next available task: {task['task_id']}")
            return task
    
    logger.info("(supervisor) - No available tasks found")
    return None


def generate_casual_response(query: str, llm_client: Get_response) -> str:
    """
    Generate a casual/helpful response for non-actionable queries.
    """
    
    try:
        logger.info("(supervisor) - Generating casual response")
        
        conversation = [
            {"role": "system", "content": GENERATE_HELPFUL},
            {"role": "user", "content": f"Customer message: {query}"}
        ]
        
        response = llm_client.invoke(conversation)
        logger.info("(supervisor) - Casual response generated")
        
        return response.strip()
    
    except Exception as e:
        logger.error(f"(supervisor) - Error generating casual response: {e}")
        return "Thank you for reaching out! How can I assist you today?"


def generate_final_response(state: AgentState, llm_client: Get_response) -> str:
    """
    Generate a comprehensive final response based on completed tasks.
    """
    
    try:
        logger.info("(supervisor) - Generating final response")
        
        # Collect results from all completed tasks
        subtasks = state.get("subtasks", [])
        task_results = [
            f"- {task['description']}: {task.get('result', 'No additional details')}"
            for task in subtasks
            if task["status"] == TaskStatus.COMPLETED
        ]
        
        task_summary = "\n".join(task_results) if task_results else "No specific actions completed."
        
        conversation = [
            {"role": "system", "content": FINAL_RESPONSE_PROMPT},
            {
                "role": "user",
                "content": f"Original query: {state.get('original_query', '')}\n\nCompleted actions:\n{task_summary}"
            }
        ]
        
        response = llm_client.invoke(conversation)
        logger.info("(supervisor) - Final response generated")
        
        return response.strip()
    
    except Exception as e:
        logger.error(f"(supervisor) - Error generating final response: {e}")
        return "Your request has been processed. Thank you for contacting us!"