import os
import sys
from typing import Any, Dict, Optional
from langchain_core.messages import HumanMessage, AIMessage

from ai_processing.get_response import Get_response
from ai_processing.states import AgentState
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_processing.graph import create_support_graph
from utils.config_loader import load_config
from utils.logger import get_logger


logger = get_logger()
config = load_config("config.yaml")
logger.info("using: %s", config['ai_processing']['model'])

# Conversation storage (will use a database)
CONVERSATION_STORE = {}  # {conversation_id: AgentState}

def initialize_state(
    query: str,
    conversation_id: str,
    llm_client=None,
    existing_state: Optional[AgentState] = None
) -> AgentState:
    """
    Initialize or retrieve conversation state.
    
    Args:
        query: User's input query
        conversation_id: Unique identifier for the conversation
        llm_client: LLM client for the supervisor
        existing_state: Existing state if continuing a conversation
    
    Returns:
        Initialized or updated AgentState
    """
    
    if existing_state:
        # Continuing an existing conversation
        logger.info(f"Resuming conversation: {conversation_id}")
        state = existing_state
        # Add new user message
        state["messages"].append(HumanMessage(content=query))
    else:
        # Starting a new conversation
        logger.info(f"Starting new conversation: {conversation_id}")
        state: AgentState = {
            "messages": [HumanMessage(content=query)],
            "original_query": query,
            "subtasks": [],
            "current_task": None,
            "next_agent": "",
            "needs_human_input": False,
            "human_input_prompt": None,
            "agent_context": {},
            "all_tasks_completed": False,
            "final_response": None,
            "llm_client": llm_client,
        }
    
    return state


def invoke_graph(
    query: str,
    conversation_id: str,
    llm_client=None,
    is_new_conversation: bool = True,
) -> dict:
    """
    Invoke the support graph with user input.
    Handles both new and resumed conversations.
    
    Args:
        query: User's input query or response
        conversation_id: Unique identifier for the conversation
        llm_client: LLM client for supervisor
        is_new_conversation: True if starting new, False if resuming
    
    Returns:
        Dictionary containing the final state and any outputs
    """
    
    logger.info(f"Invoking graph for conversation: {conversation_id}")
    
    # Get existing state if resuming
    existing_state = CONVERSATION_STORE.get(conversation_id) if not is_new_conversation else None
    state = initialize_state(query, conversation_id, llm_client, existing_state)
    
    # Check if resuming and human input was required
    if existing_state and state.get("needs_human_input", False):
        logger.info(f"Resuming with human input for conversation: {conversation_id}")
        # The human input has been added to messages
        # Clear the flag so it doesn't loop
        state["needs_human_input"] = False
    
    # Create and compile the graph
    graph = create_support_graph()
    
    # Invoke the graph with streaming
    logger.info("Starting graph execution...")
    
    try:
        # Run the graph
        final_state = None
        for output in graph.stream(
            state,
            config={"configurable": {"thread_id": conversation_id}}
        ):
            # Process each step of the graph
            node_name, node_output = next(iter(output.items()))
            logger.info(f"Node executed: {node_name}")
            final_state = node_output
            
            # Check if human input is needed mid-execution
            if node_output.get("needs_human_input", False):
                logger.info(f"Human input required: {node_output.get('human_input_prompt')}")
                # Store state for later resumption
                CONVERSATION_STORE[conversation_id] = node_output
                
                return {
                    "status": "awaiting_human_input",
                    "conversation_id": conversation_id,
                    "prompt": node_output.get("human_input_prompt"),
                    "state": node_output,
                }
        
        # Graph execution completed
        logger.info("Graph execution completed successfully")
        
        # Store final state
        CONVERSATION_STORE[conversation_id] = final_state
        
        return {
            "status": "completed",
            "conversation_id": conversation_id,
            "response": final_state.get("final_response"),
            "state": final_state,
        }
    
    except Exception as e:
        logger.error(f"Error during graph execution: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "conversation_id": conversation_id,
            "error": str(e),
        }


def main():
    """
    Main entry point for the support bot.
    Demonstrates conversation flow with human-in-the-loop.
    """
    
    conversation_id = "conv_001"
    llm_client = None  # Initialize your LLM client here
    
    print("=== Customer Support Bot ===\n")
    
    # Start a new conversation
    print("User: My laptop won't turn on")
    result = invoke_graph(
        query="My laptop won't turn on",
        conversation_id=conversation_id,
        llm_client=llm_client,
        is_new_conversation=True,
    )
    
    print(f"Status: {result['status']}")
    if result['status'] == "awaiting_human_input":
        print(f"Bot: {result['prompt']}\n")
        
        # Simulate human response
        print("User: Yes, I've tried restarting it")
        result = invoke_graph(
            query="Yes, I've tried restarting it",
            conversation_id=conversation_id,
            llm_client=llm_client,
            is_new_conversation=False,  # Resuming conversation
        )
    
    if result['status'] == "completed":
        print(f"Bot: {result['response']}")
    elif result['status'] == "error":
        print(f"Error: {result['error']}")
    
    print(f"\nFinal state summary:")
    print(f"Total messages: {len(result['state']['messages'])}")
    print(f"Subtasks created: {len(result['state']['subtasks'])}")
    print(f"All tasks completed: {result['state']['all_tasks_completed']}")


def interactive_mode():
    """
    Interactive mode for continuous conversations.
    """
    
    print("=== Customer Support Bot (Interactive Mode) ===\n")
    print("Type 'quit' to exit\n")
    
    conversation_id = "conv_interactive"
    llm_client = None  # Initialize your LLM client here
    is_new = True
    
    while True:
        user_input = input("You: ").strip()
        
        if user_input.lower() == 'quit':
            print("Goodbye!")
            break
        
        if not user_input:
            continue
        
        # Invoke graph
        result = invoke_graph(
            query=user_input,
            conversation_id=conversation_id,
            llm_client=llm_client,
            is_new_conversation=is_new,
        )
        
        is_new = False  # After first message, always resume
        
        if result['status'] == "awaiting_human_input":
            print(f"Bot: {result['prompt']}")
        
        elif result['status'] == "completed":
            print(f"Bot: {result['response']}\n")
        
        elif result['status'] == "error":
            print(f"Error: {result['error']}\n")


if __name__ == "__main__":
    # Run in demo mode
    main()
    
    # Uncomment below to run in interactive mode
    # interactive_mode()