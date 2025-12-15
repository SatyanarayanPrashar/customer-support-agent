import json
import re
from typing import Dict, Any, List, Callable
from ai_processing.states import AgentState, TaskStatus
from utils.logger import get_logger

logger = get_logger()

class BaseAgentNode:
    def __init__(
        self, 
        name: str,
        system_prompt: str,
        tools_schema: List[Dict],
        tool_func_map: Dict[str, Callable],
        llm_client: Any,
        chat_manager: Any,
        retriever: Any
    ):
        self.name = name
        self.system_prompt = system_prompt
        self.tools_schema = tools_schema
        self.tool_func_map = tool_func_map # Maps tool names to actual python functions
        self.llm_client = llm_client
        self.chat_manager = chat_manager
        self.retriever = retriever

    def __call__(self, state: AgentState) -> AgentState:
        """
        Makes the class instance callable so it works directly as a LangGraph node.
        """
        return self.process_request(state)

    def process_request(self, state: AgentState) -> AgentState:
        current_task = state["current_task"]
        
        if not self.llm_client:
            logger.error(f"({self.name}) - LLM client not found")
            return state

        logger.info(f"({self.name}) - Processing task: {current_task}")

        try:
            analysis = self._analyze_request(state)
            
            # Default fallback if analysis fails
            if "error" in analysis:
                raise Exception(analysis["error"])

            action = analysis.get("action", "respond")
            message_to_user = analysis.get("message", str(analysis))
            
            # Log assistant output to history
            self.chat_manager.add_message("assistant", json.dumps(analysis))

            if action == "need_info":
                state["needs_human_input"] = True
                state["human_input_prompt"] = message_to_user
                current_task["status"] = TaskStatus.BLOCKED
                
            elif action == "respond":
                state["needs_human_input"] = True
                state["human_input_prompt"] = message_to_user
                current_task["status"] = TaskStatus.BLOCKED

            elif action == "completed":
                self._mark_task_completed(state, current_task, message_to_user)
            
            else:
                # Default behavior for unknown actions
                state["needs_human_input"] = True

        except Exception as e:
            logger.error(f"({self.name}) - error: {e}")
            error_msg = f"I encountered an error while processing your request in {self.name}. Please try again."
            self.chat_manager.add_message("developer", error_msg)
            self._mark_task_completed(state, current_task, error_msg)
        
        return state

    def _analyze_request(self, state: AgentState) -> Dict:
        history = self.chat_manager.get_thread_messages(self.llm_client)

        # Context Extraction (RAG)
        if not state.get("agent_context"):
            logger.info(f"({self.name}) - Extracting context")
            user_message = history[0]["content"] if history else ""
            state["agent_context"] = self.retriever.extract(user_message)

        # Prepare Conversation
        conversation = [
            {"role": "system", "content": self.system_prompt.format(context=state.get("agent_context", ""))},
            *history
        ]
        
        # Invoke LLM
        response = self.llm_client.invoke(input_list=conversation, tools=self.tools_schema)

        # Handle Function Calls
        tool_calls = [item for item in response.output if item.type == 'function_call']

        if tool_calls:
            logger.info(f"({self.name}) - {len(tool_calls)} Function calls detected.")
            for item in tool_calls:
                self._handle_tool_execution(item)
            return self._analyze_request(state)
        
        # Parse Text Response
        return self._parse_llm_response(response)

    def _handle_tool_execution(self, item):
        tool_name = item.name
        try:
            params = json.loads(item.arguments)
            
            if tool_name in self.tool_func_map:
                logger.info(f"({self.name}) - Executing tool: {tool_name}")
                func = self.tool_func_map[tool_name]
                result = func(**params) 
            else:
                result = f"Error: Unknown tool {tool_name}"
                
        except Exception as e:
            result = f"Error execution failed: {str(e)}"

        self.chat_manager.add_message("developer", f"Tool '{tool_name}' result: {result}")

    def _parse_llm_response(self, response) -> Dict:
        try:
            raw_text = response.output[0].content[0].text
            clean_text = raw_text.strip()
            # Remove markdown code blocks
            clean_text = re.sub(r"^```(?:json)?", "", clean_text)
            clean_text = re.sub(r"```$", "", clean_text).strip()
            return json.loads(clean_text)
        except (AttributeError, IndexError):
            return {"error": "Empty response from LLM"}
        except json.JSONDecodeError:
            # Simple repair attempt
            logger.warning(f"JSON parse failed, attempting repair: {clean_text}")
            safe_response = re.sub(r"(?<!\\)'", '"', clean_text)
            return json.loads(safe_response) if clean_text else {"error": "Failed to parse JSON"}

    def _mark_task_completed(self, state: AgentState, task: Dict, result: str):
        for t in state.get("subtasks", []):
            if t["task_id"] == task["task_id"]:
                t["status"] = "completed"
                t["result"] = result
                break
        state["current_task"] = None