from typing import Dict, List, TypedDict
from langgraph.graph import MessagesState

class CafeState(MessagesState):
    session_id: str
    cart: Dict[int, int]  # item_id -> quantity
    current_agent: str
    total_amount: float
    reasoning: str = ""
