import json
import os
import sys
from typing import Any, Dict

from ai_processing.llm_client import LLM_Client
from ai_processing.states import AgentState
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_processing.graph import create_support_graph
from utils.config_loader import load_config
from utils.logger import get_logger

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
        self.llm_client = LLM_Client(config)
        self.graph = create_support_graph()
        self.conversation_active = True
        self.state = None
        
    def initialize_conversation(self):
        """Initialize a new conversation state"""
        self.state = AgentState(
            messages=[],
            subtasks=[],
            current_task=None,
            next_agent="supervisor",
            needs_human_input=False,
            human_input_prompt=None,
            agent_context={},
            all_tasks_completed=False,
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
            print("\nconveresation: \n")
            for i in self.state["messages"]:
                print(i)
                print("\n------------------------------------------------------------------------------------------------------------------------\n")
            print("\n\nagent context:\n", self.state["agent_context"])
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
        
        if self.state is None:
            # Check if we were awaiting a real query
            if self.state and self.state.get("awaiting_real_query"):
                self.state["messages"].append({"role": "user", "content": user_message})
                self.state["all_tasks_completed"] = False
                self.state["subtasks"] = []
            else:
                self.initialize_conversation()
                self.state["messages"].append({"role": "user", "content": user_message})
        else:
            # Continue existing conversation
            self.state["messages"].append({"role": "user", "content": user_message})

        self.state["needs_human_input"] = False 
        
        if self.state.get("current_task"):
            self.state["current_task"]["status"] = "in_progress"
            for t in self.state["subtasks"]:
                if t["task_id"] == self.state["current_task"]["task_id"]:
                    t["status"] = "in_progress"

        previous_message_count = len(self.state["messages"])
        
        try:
            result = self.graph.invoke(self.state, {"recursion_limit": 100})
            self.state = result
            
            current_messages = result["messages"]
            new_messages_count = len(current_messages) - previous_message_count

            if new_messages_count > 0:
                new_messages = current_messages[-new_messages_count:]
                for msg in new_messages:
                    if msg["role"] == "assistant":
                        content_str = msg["content"]
                        try:
                            content_dict = json.loads(content_str)
                            print(f"\nAssistant: {content_dict.get('message', 'No message provided')}\n")
                            
                        except json.JSONDecodeError:
                            print(f"\nAssistant: {content_str}\n")
                        except Exception as e:
                            print(f"\nAssistant (Error parsing response): {content_str}\n")

            if result.get("needs_human_input"):
                return True
            
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