from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
import os
from apps.agentic_barista.agents.coordinator import BaristaCoordinator
from apps.agentic_barista.models import MenuItem, Order
from services.state_store import state_store

router = APIRouter()

# In-memory cart storage (session_id -> cart)
cart_storage: Dict[str, Dict[int, int]] = {}

class ChatRequest(BaseModel):
    message: str
    session_id: str
    model: Optional[str] = "gemini-2.0-flash-exp"

class MenuResponse(BaseModel):
    items: list

def _normalize_cart_keys(cart: Dict) -> Dict[int, int]:
    normalized: Dict[int, int] = {}
    for key, value in (cart or {}).items():
        try:
            item_id = int(key)
        except (TypeError, ValueError):
            continue
        try:
            qty = int(value)
        except (TypeError, ValueError):
            continue
        if qty > 0:
            normalized[item_id] = qty
    return normalized

def _get_cart_ttl_seconds() -> int:
    try:
        return int(os.getenv("CART_TTL_SECONDS", "86400"))
    except ValueError:
        return 86400

@router.post("/chat")
async def chat(request: ChatRequest):
    try:
        coordinator = BaristaCoordinator(model_name=request.model)

        cart_key = state_store.key(app="barista", session_id=request.session_id, kind="cart")
        use_redis = False
        try:
            use_redis = await state_store.available()
        except Exception:
            use_redis = False

        if not use_redis:
            if request.session_id not in cart_storage:
                cart_storage[request.session_id] = {}
            cart = cart_storage[request.session_id]
        else:
            cart = _normalize_cart_keys(await state_store.get_json(cart_key, default={}))
        
        # Process message
        result = await coordinator.process_message(
            request.message,
            request.session_id,
            cart,
            request.model
        )

        # Persist cart
        if not use_redis:
            cart_storage[request.session_id] = result["cart"]
        else:
            if result["cart"]:
                await state_store.set_json(cart_key, result["cart"], ttl_seconds=_get_cart_ttl_seconds())
            else:
                await state_store.delete(cart_key)
        
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
