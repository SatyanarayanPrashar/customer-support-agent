from ai_processing.states import AgentState, AgentType, TaskStatus
from langchain_core.messages import HumanMessage, AIMessage

def billing_agent(state: AgentState) -> AgentState:
    """
    Billing agent - handles payment, invoices, refunds
    """
    
    current_task = state["current_task"]
    
    # Simulate billing logic
    result = "I've reviewed your billing. Your last payment of $99.99 was processed on Oct 15. No outstanding balance."
    
    # Update task
    for task in state["subtasks"]:
        if task["task_id"] == current_task["task_id"]:
            task["status"] = TaskStatus.COMPLETED
            task["result"] = result
    
    state["messages"].append(AIMessage(content=result))
    state["next_agent"] = AgentType.SUPERVISOR
    state["current_task"] = None
    
    return state
