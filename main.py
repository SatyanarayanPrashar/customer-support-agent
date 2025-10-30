import os
import sys
from typing import Any, Dict
from langchain_core.messages import HumanMessage, AIMessage

from ai_processing.get_response import Get_response
from ai_processing.states import AgentState
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.graph import create_support_graph
from utils.config_loader import load_config
from utils.logger import get_logger

from langchain_core.messages import HumanMessage

logger = get_logger()
config = load_config("config.yaml")
logger.info("using: %s", config['ai_processing']['model'])
"""
Interactive Terminal Chatbot with Multi-Agent Support System
Provides a conversational interface where users can chat with the support system
"""

class InteractiveSupportChatbot:
    """
    Interactive chatbot that maintains conversation state and handles user input
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the chatbot with configuration
        
        Args:
            config: Configuration with API keys and model settings
        """
        self.config = config
        self.llm_client = Get_response(config)
        self.graph = create_support_graph()
        self.conversation_active = True
        self.state = None
        
    def initialize_conversation(self):
        """Initialize a new conversation state"""
        self.state = AgentState(
            messages=[],
            original_query="",
            subtasks=[],
            current_task=None,
            next_agent="supervisor",
            needs_human_input=False,
            human_input_prompt=None,
            agent_context={},
            all_tasks_completed=False,
            final_response=None,
            llm_client=self.llm_client,
            casual_turn_count=0,
            awaiting_real_query=False
        )

    def get_user_input(self, prompt: str = "You: ") -> str:
        """
        Get input from user with proper formatting
        
        Args:
            prompt: The prompt to display
            
        Returns:
            User's input string
        """
        try:
            user_input = input(prompt).strip()
            return user_input
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye!")
            sys.exit(0)
    
    def process_user_message(self, user_message: str) -> bool:
        """
        Process a user message through the multi-agent system
        
        Args:
            user_message: The user's input message
            
        Returns:
            True if conversation should continue, False otherwise
        """
        # Check for exit commands
        if user_message.lower() in ['quit', 'exit', 'bye', 'goodbye']:
            print("Thank you for contacting support. Have a great day!")
            return False
        
        # If this is a new conversation or previous tasks are completed
        if self.state is None or not self.state.get("original_query"):
            # Check if we were awaiting a real query
            if self.state and self.state.get("awaiting_real_query"):
                # Continue with existing state to preserve casual_turn_count
                self.state["original_query"] = user_message
                self.state["messages"].append(HumanMessage(content=user_message))
                self.state["all_tasks_completed"] = False
                self.state["subtasks"] = []  # Reset subtasks
            else:
                # Fresh start
                self.initialize_conversation()
                self.state["original_query"] = user_message
                self.state["messages"].append(HumanMessage(content=user_message))
        else:
            # Continue existing conversation
            self.state["messages"].append(HumanMessage(content=user_message))
        
        try:
            # logger.info(f" - (main) - Before graph.invoke -> original_query: {self.state.get('original_query')}")
            result = self.graph.invoke(self.state)
            self.state = result
            
            # Display only new messages (messages added after user's last message)
            # Get the last assistant message
            for msg in reversed(result["messages"]):
                if isinstance(msg, AIMessage):
                    print(f"\nAssistant: {msg.content}\n")
                    break
            
            # Check if tasks are completed
            if result.get("all_tasks_completed"):
                # If we're just in casual conversation, don't ask follow-up
                if result.get("awaiting_real_query"):
                    # Just waiting for a real query, don't prompt
                    return True
                
                # Real tasks were completed, ask for follow-up
                follow_up = self.get_user_input("Do you need help with anything else? (yes/no): ")
                
                if follow_up.lower() in ['no', 'n', 'nope', 'nah']:
                    print("Thank you for contacting support. Have a great day!")
                    return False
                elif follow_up.lower() in ['yes', 'y', 'yeah', 'sure', 'yep']:
                    print("What else can I help you with?")
                    # Reset for new query but preserve conversation
                    self.state["all_tasks_completed"] = False
                    self.state["subtasks"] = []
                    self.state["casual_turn_count"] = 0
                    self.state["awaiting_real_query"] = False
            
            return True
            
        except Exception as e:
            logger.error(f" - (main) - Error processing message: {e}")
            print("I apologize, but I encountered an error. Could you please rephrase your question?")
            return True
    
    def run(self):
        """
        Main loop for the interactive chatbot
        """
        print(f"Welcome\n")
        self.initialize_conversation()
        
        while self.conversation_active:
            # Get user input
            user_message = self.get_user_input("You: ")
            
            if not user_message:
                continue
            
            # Process the message
            should_continue = self.process_user_message(user_message)
            
            if not should_continue:
                self.conversation_active = False

if __name__ == "__main__":
    config = load_config("config.yaml")
    try:
        chatbot = InteractiveSupportChatbot(config)
        chatbot.run()  
    except KeyboardInterrupt:
        print("\n\nChatbot terminated by user. Goodbye!")
    except Exception as e:
        logger.error(f" - (main) - Fatal error in chatbot: {e}")
        print(f"\nAn error occurred: {e}")
        print("Please restart the chatbot.")