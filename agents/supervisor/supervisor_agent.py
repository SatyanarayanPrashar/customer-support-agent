from ai_processing.states import AgentState, AgentType, SubTask, TaskStatus
from langchain_core.messages import HumanMessage, AIMessage
from typing import List, Optional

def supervisor_node(state: AgentState) -> AgentState:
    """
    The supervisor agent that:
    1. Analyzes the user query
    2. Decomposes it into subtasks
    3. Determines task dependencies and order
    4. Routes to the next available agent
    """
    
    # If this is the first time supervisor is called
    if not state.get("subtasks"):
        # Decompose the query into subtasks
        # In production, use LLM to analyze and decompose
        subtasks = decompose_query(state["original_query"])
        state["subtasks"] = subtasks
    
    # Find the next task to execute
    next_task = get_next_task(state["subtasks"])
    
    if next_task is None:
        # All tasks completed
        state["all_tasks_completed"] = True
        state["next_agent"] = "finish"
        state["final_response"] = compile_final_response(state)
    else:
        # Update task status
        for task in state["subtasks"]:
            if task["task_id"] == next_task["task_id"]:
                task["status"] = TaskStatus.IN_PROGRESS
        
        state["current_task"] = next_task
        state["next_agent"] = next_task["agent"]
        
        # Add supervisor message explaining what we're doing
        state["messages"].append(
            AIMessage(content=f"Let me help you with that. First, I'll {next_task['description']}.")
        )
    
    return state

def decompose_query(query: str) -> List[SubTask]:
    """
    Decompose user query into subtasks.
    In production, use an LLM to intelligently parse and decompose.
    
    Example logic (simplified):
    - "product not working" -> troubleshoot task
    - "warranty status" -> warranty task
    - "billing issue" -> billing task
    """
    
    # This is a simplified version. In production, use LLM with a prompt like:
    # "Analyze this query and break it into discrete tasks. For each task, 
    #  identify which specialized agent should handle it and any dependencies."
    
    tasks = []
    query_lower = query.lower()
    task_counter = 1
    
    # Check for troubleshooting needs
    if any(word in query_lower for word in ["not working", "broken", "issue", "problem", "error"]):
        tasks.append(SubTask(
            task_id=f"task_{task_counter}",
            description="troubleshoot the product issue",
            agent=AgentType.TROUBLESHOOT,
            status=TaskStatus.PENDING,
            result=None,
            dependencies=[],
            priority=1  # Troubleshooting usually comes first
        ))
        task_counter += 1
    
    # Check for warranty queries
    if any(word in query_lower for word in ["warranty", "coverage", "guarantee"]):
        tasks.append(SubTask(
            task_id=f"task_{task_counter}",
            description="check warranty status",
            agent=AgentType.WARRANTY,
            status=TaskStatus.PENDING,
            result=None,
            dependencies=[f"task_1"] if tasks else [],  # Depends on troubleshoot if it exists
            priority=2
        ))
        task_counter += 1
    
    # Check for billing queries
    if any(word in query_lower for word in ["bill", "charge", "payment", "invoice", "refund"]):
        tasks.append(SubTask(
            task_id=f"task_{task_counter}",
            description="handle billing inquiry",
            agent=AgentType.BILLING,
            status=TaskStatus.PENDING,
            result=None,
            dependencies=[],
            priority=2
        ))
        task_counter += 1
    
    # Check for return requests
    if any(word in query_lower for word in ["return", "send back", "return policy"]):
        tasks.append(SubTask(
            task_id=f"task_{task_counter}",
            description="process return request",
            agent=AgentType.RETURNS,
            status=TaskStatus.PENDING,
            result=None,
            dependencies=[f"task_1"] if tasks else [],  # May depend on troubleshoot
            priority=3
        ))
        task_counter += 1
    
    return tasks

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


def compile_final_response(state: AgentState) -> str:
    """Compile results from all agents into a final response"""
    
    response_parts = ["Here's a summary of what we've addressed:\n"]
    
    for task in state["subtasks"]:
        if task["status"] == TaskStatus.COMPLETED and task["result"]:
            response_parts.append(f"- {task['description'].capitalize()}: {task['result']}")
    
    response_parts.append("\nIs there anything else I can help you with?")
    
    return "\n".join(response_parts)
