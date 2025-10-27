from ai_processing.states import AgentState, AgentType, TaskStatus
from langchain_core.messages import HumanMessage, AIMessage

def warranty_agent(state: AgentState) -> AgentState:
    """
    Warranty agent - checks warranty status and coverage
    """
    
    current_task = state["current_task"]
    
    # Check if product needs replacement based on troubleshoot results
    issue_context = ""
    if state["agent_context"].get("issue_resolved") == False:
        issue_context = " Since troubleshooting didn't resolve the issue, you may be eligible for a replacement."
    
    # Simulate warranty check
    result = f"Your product is under warranty until Dec 2025. It covers manufacturing defects.{issue_context}"
    
    # Update task
    for task in state["subtasks"]:
        if task["task_id"] == current_task["task_id"]:
            task["status"] = TaskStatus.COMPLETED
            task["result"] = result
    
    state["messages"].append(AIMessage(content=result))
    state["next_agent"] = AgentType.SUPERVISOR
    state["current_task"] = None
    
    return state
