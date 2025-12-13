from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
import json
import os
from redis.asyncio import Redis, from_url
from apps.agentic_barista.agents.coordinator import BaristaCoordinator
from apps.agentic_barista.models import MenuItem, Order

router = APIRouter()

# In-memory cart storage (session_id -> cart)
cart_storage: Dict[str, Dict[int, int]] = {}
_redis_client: Optional[Redis] = None

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

def _build_redis_url() -> Optional[str]:
    url = os.getenv("REDIS_URL", "").strip()
    if url:
        return url
    host = os.getenv("REDIS_HOST", "").strip()
    if not host:
        return None
    port = os.getenv("REDIS_PORT", "6379").strip() or "6379"
    tls = os.getenv("REDIS_TLS", "true").strip().lower() in {"1", "true", "yes", "y"}
    scheme = "rediss" if tls else "redis"
    return f"{scheme}://{host}:{port}/0"

async def _get_redis() -> Optional[Redis]:
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    redis_url = _build_redis_url()
    if not redis_url:
        return None

    client = from_url(redis_url, encoding="utf-8", decode_responses=True)
    await client.ping()
    _redis_client = client
    return _redis_client

def _cart_key(session_id: str) -> str:
    return f"barista:cart:{session_id}"

@router.post("/chat")
async def chat(request: ChatRequest):
    try:
        coordinator = BaristaCoordinator(model_name=request.model)

        redis_client = await _get_redis()
        if redis_client is None:
            if request.session_id not in cart_storage:
                cart_storage[request.session_id] = {}
            cart = cart_storage[request.session_id]
        else:
            raw_cart = await redis_client.get(_cart_key(request.session_id))
            cart = _normalize_cart_keys(json.loads(raw_cart) if raw_cart else {})
        
        # Process message
        result = await coordinator.process_message(
            request.message,
            request.session_id,
            cart,
            request.model
        )

        # Persist cart
        if redis_client is None:
            cart_storage[request.session_id] = result["cart"]
        else:
            if result["cart"]:
                await redis_client.set(
                    _cart_key(request.session_id),
                    json.dumps(result["cart"]),
                    ex=_get_cart_ttl_seconds(),
                )
            else:
                await redis_client.delete(_cart_key(request.session_id))
        
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
