from typing import Literal
from langgraph.graph import StateGraph, START, END
from apps.agentic_barista.graph.state import CafeState
from apps.agentic_barista.agents.menu_agent import MenuAgent
from apps.agentic_barista.agents.order_agent import OrderAgent
from apps.agentic_barista.agents.confirmation_agent import ConfirmationAgent
from langchain_core.messages import HumanMessage, AIMessage
import google.generativeai as genai
from config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

class BaristaCoordinator:
    def __init__(self, model_name: str = "gemini-2.0-flash-exp"):
        self.menu_agent = MenuAgent()
        self.order_agent = OrderAgent()
        self.confirmation_agent = ConfirmationAgent()
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(CafeState)
        
        workflow.add_node("router", self._route_message)
        workflow.add_node("menu", self._menu_node)
        workflow.add_node("order", self._order_node)
        workflow.add_node("confirmation", self._confirmation_node)
        workflow.add_node("general", self._general_node)
        
        workflow.add_edge(START, "router")
        workflow.add_conditional_edges(
            "router",
            self._decide_next,
            {
                "menu": "menu",
                "order": "order",
                "confirmation": "confirmation",
                "general": "general",
                "end": END
            }
        )
        workflow.add_edge("menu", END)
        workflow.add_edge("order", END)
        workflow.add_edge("confirmation", END)
        workflow.add_edge("general", END)
        
        return workflow.compile()
    
    async def _route_message(self, state: CafeState) -> CafeState:
        last_message = state["messages"][-1].content if state["messages"] else ""
        
        # Use AI to determine intent
        prompt = f"""You are a barista assistant coordinator. Analyze the user's message and determine the intent.

User message: "{last_message}"

Classify into ONE of these intents:
- MENU: User wants to see menu, browse items, ask about specific drinks/food
- ORDER: User wants to add/remove items, view cart, modify order
- CONFIRM: User wants to confirm/place/complete their order
- GENERAL: General questions, greetings, chitchat (not related to menu/ordering)

Respond with ONLY the intent word (MENU, ORDER, CONFIRM, or GENERAL) and a brief reasoning.
Format: INTENT: <intent>
REASONING: <one sentence explanation>"""

        try:
            ai_response = self.model.generate_content(prompt).text
            
            # Parse response
            if "MENU" in ai_response.upper():
                state["current_agent"] = "menu"
            elif "CONFIRM" in ai_response.upper():
                state["current_agent"] = "confirmation"
            elif "ORDER" in ai_response.upper():
                state["current_agent"] = "order"
            else:
                state["current_agent"] = "general"
            
            # Extract reasoning
            if "REASONING:" in ai_response:
                reasoning = ai_response.split("REASONING:")[1].strip()
                state["reasoning"] = reasoning
            else:
                state["reasoning"] = "Analyzing user intent..."
                
        except Exception as e:
            # Fallback to keyword matching
            if any(word in last_message.lower() for word in ["menu", "show me", "what do you have", "items", "drinks"]):
                state["current_agent"] = "menu"
            elif any(word in last_message.lower() for word in ["confirm", "place order", "checkout", "complete"]):
                state["current_agent"] = "confirmation"
            elif any(word in last_message.lower() for word in ["add", "cart", "remove", "delete"]):
                state["current_agent"] = "order"
            else:
                state["current_agent"] = "general"
            state["reasoning"] = "Using keyword-based intent detection."
        
        return state
    
    def _decide_next(self, state: CafeState) -> Literal["menu", "order", "confirmation", "general", "end"]:
        return state.get("current_agent", "general")
    
    async def _menu_node(self, state: CafeState) -> CafeState:
        last_message = state["messages"][-1].content
        response = await self.menu_agent.process(last_message, state)
        state["messages"].append(AIMessage(content=response))
        return state
    
    async def _order_node(self, state: CafeState) -> CafeState:
        last_message = state["messages"][-1].content
        response = await self.order_agent.process(last_message, state)
        state["messages"].append(AIMessage(content=response))
        return state
    
    async def _confirmation_node(self, state: CafeState) -> CafeState:
        last_message = state["messages"][-1].content
        response = await self.confirmation_agent.process(last_message, state)
        state["messages"].append(AIMessage(content=response))
        return state
    
    async def _general_node(self, state: CafeState) -> CafeState:
        """Handle general questions conversationally"""
        last_message = state["messages"][-1].content
        
        prompt = f"""You are a friendly barista assistant. The user asked a general question that doesn't require menu browsing or ordering.

User question: "{last_message}"

Respond conversationally and helpfully. Keep it brief (2-3 sentences). Be warm and coffee-themed when appropriate.
If they're asking about coffee in general, share interesting facts. If it's a greeting, be friendly."""

        try:
            response = self.model.generate_content(prompt).text
        except:
            response = "I'm here to help you with our menu and orders! Feel free to ask me anything about coffee or our offerings."
        
        state["messages"].append(AIMessage(content=response))
        return state
    
    async def process_message(self, message: str, session_id: str, cart: dict, model_name: str = "gemini-2.0-flash-exp") -> dict:
        # Update model if different
        if model_name != self.model_name:
            self.model_name = model_name
            self.model = genai.GenerativeModel(model_name)
        
        initial_state = CafeState(
            messages=[HumanMessage(content=message)],
            session_id=session_id,
            cart=cart,
            current_agent="",
            total_amount=0.0
        )
        
        result = await self.graph.ainvoke(initial_state)
        
        response_message = result["messages"][-1].content
        reasoning = result.get("reasoning", "")
        
        return {
            "response": response_message,
            "cart": result.get("cart", {}),
            "total_amount": result.get("total_amount", 0.0),
            "agent": result.get("current_agent", "unknown"),
            "reasoning": reasoning
        }
