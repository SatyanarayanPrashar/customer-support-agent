import json
from typing import Dict, List
from agents.billing._tools.billing_tools import get_bill_by_id, get_bills, refund_ticket, send_bill
from agents.billing.prompt import BILLING_ANALYSIS_PROMPT, BILLING_RESPONSE_PROMPT
from ai_processing.states import AgentState, AgentType, TaskStatus
from langchain_core.messages import HumanMessage, AIMessage

from utils.logger import get_logger
logger = get_logger()

def billing_agent(state: "AgentState") -> "AgentState":
    return state