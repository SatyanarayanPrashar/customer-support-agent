from agents.base_agent import BaseAgentNode
from agents.troubleshoot.prompt import TROUBLESHOOTING_AGENT_PROMPT
from agents.troubleshoot._tools.troubleshoot_tools import TROUBLESHOOT_TOOLS_SCHEMA, TROUBLESHOOT_TOOL_MAP

def create_troubleshoot_node(llm_client, chat_manager, retriever):
    """
    Returns a configured instance of the Billing Agent Node.
    """
    return BaseAgentNode(
        name="troubleshoot",
        system_prompt=TROUBLESHOOTING_AGENT_PROMPT,
        tools_schema=TROUBLESHOOT_TOOLS_SCHEMA,
        tool_func_map=TROUBLESHOOT_TOOL_MAP,
        llm_client=llm_client,
        chat_manager=chat_manager,
        retriever=retriever
    )