from agents.base_agent import BaseAgentNode
from agents.billing.prompt import BILLING_ANALYSIS_PROMPT
from agents.billing._tools.billing_tools import BILLING_TOOLS_SCHEMA, BILLING_TOOL_MAP

def create_billing_node(llm_client, chat_manager, retriever):
    """
    Returns a configured instance of the Billing Agent Node.
    """
    return BaseAgentNode(
        name="billing",
        system_prompt=BILLING_ANALYSIS_PROMPT,
        tools_schema=BILLING_TOOLS_SCHEMA,
        tool_func_map=BILLING_TOOL_MAP,
        llm_client=llm_client,
        chat_manager=chat_manager,
        retriever=retriever
    )