from typing import Dict, List, TypedDict
from langgraph.graph import MessagesState

class CafeState(MessagesState):
    session_id: str
    user_id: int | None
    cart: Dict[int, int]  # item_id -> quantity
    current_agent: str
    total_amount: float
    reasoning: str = ""
    last_order_id: int | None
    ai_error: str | None
