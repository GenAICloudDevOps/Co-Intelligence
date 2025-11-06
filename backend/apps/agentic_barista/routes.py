from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
from apps.agentic_barista.agents.coordinator import BaristaCoordinator
from apps.agentic_barista.models import MenuItem, Order

router = APIRouter()

# In-memory cart storage (session_id -> cart)
cart_storage: Dict[str, Dict[int, int]] = {}

class ChatRequest(BaseModel):
    message: str
    session_id: str
    model: Optional[str] = "gemini-2.0-flash-exp"

class MenuResponse(BaseModel):
    items: list

@router.post("/chat")
async def chat(request: ChatRequest):
    try:
        coordinator = BaristaCoordinator(model_name=request.model)
        
        # Get or initialize cart
        if request.session_id not in cart_storage:
            cart_storage[request.session_id] = {}
        
        cart = cart_storage[request.session_id]
        
        # Process message
        result = await coordinator.process_message(
            request.message,
            request.session_id,
            cart,
            request.model
        )
        
        # Update cart storage
        cart_storage[request.session_id] = result["cart"]
        
        return {
            "response": result["response"],
            "cart": result["cart"],
            "total_amount": result["total_amount"],
            "agent": result["agent"],
            "reasoning": result.get("reasoning", ""),
            "session_id": request.session_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/menu")
async def get_menu():
    items = await MenuItem.filter(available=True).all()
    return {
        "items": [
            {
                "id": item.id,
                "name": item.name,
                "description": item.description,
                "price": float(item.price),
                "category": item.category
            }
            for item in items
        ]
    }

@router.get("/orders/{session_id}")
async def get_orders(session_id: str):
    orders = await Order.filter(session_id=session_id).all()
    return {
        "orders": [
            {
                "id": order.id,
                "items": order.items,
                "total": float(order.total),
                "status": order.status,
                "created_at": order.created_at.isoformat()
            }
            for order in orders
        ]
    }
