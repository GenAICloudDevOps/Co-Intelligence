from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict
import os
from apps.agentic_barista.agents.coordinator import BaristaCoordinator
from apps.agentic_barista.models import MenuItem, Order
from auth.models import User
from auth.utils import get_current_user_optional
from services.state_store import state_store
from services.email_notifications import email_notifications

router = APIRouter()

# In-memory cart storage (session_id -> cart)
cart_storage: Dict[str, Dict[int, int]] = {}

class ChatRequest(BaseModel):
    message: str
    session_id: str
    model: Optional[str] = None

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
async def chat(request: ChatRequest, background_tasks: BackgroundTasks, current_user: User | None = Depends(get_current_user_optional)):
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
            request.model,
            user_id=current_user.id if current_user else None,
        )

        # Persist cart
        if not use_redis:
            cart_storage[request.session_id] = result["cart"]
        else:
            if result["cart"]:
                await state_store.set_json(cart_key, result["cart"], ttl_seconds=_get_cart_ttl_seconds())
            else:
                await state_store.delete(cart_key)
        
        order_id = result.get("order_id")
        if order_id and current_user:
            order = await Order.get_or_none(id=order_id)
            if order:
                # Import notification services
                from services.notification_prefs import notification_prefs
                from services.in_app_notifications import in_app_notifications
                from services.slack_notifications import slack_notifications

                items_summary = ""
                for item in (order.items or []):
                    qty = item.get("quantity")
                    name = item.get("name")
                    line_total = item.get("total")
                    if qty and name:
                        items_summary += f"- {qty}x {name}"
                        if line_total is not None:
                            try:
                                items_summary += f" (${float(line_total):.2f})"
                            except Exception:
                                pass
                        items_summary += "\n"

                app_id = "agentic-barista"

                # Check per-app email preference
                if await notification_prefs.should_send_email(current_user.id, app_id):
                    background_tasks.add_task(
                        email_notifications.send_text_email_safe,
                        current_user.email,
                        "Barista order confirmed",
                        f"Hi {current_user.username},\n\nYour coffee order is confirmed (Order #{order.id}).\n\nItems:\n{items_summary}\nTotal: ${float(order.total):.2f}\n\nThanks,\nCo-Intelligence",
                    )

                # Check per-app in-app notification preference
                if await notification_prefs.should_send_in_app(current_user.id, app_id):
                    await in_app_notifications.create_notification(
                        user_id=current_user.id,
                        app_id=app_id,
                        title=f"Order #{order.id} confirmed",
                        message=f"Your coffee order (${float(order.total):.2f}) is confirmed!",
                        link=f"/apps/agentic-barista?order={order.id}",
                    )

                # Check per-app Slack notification preference
                if await notification_prefs.should_send_slack(current_user.id, app_id):
                    background_tasks.add_task(
                        slack_notifications.send_barista_order_notification,
                        order.id,
                        current_user.username,
                        float(order.total),
                        len(order.items or []),
                    )

        return {
            "response": result["response"],
            "cart": result["cart"],
            "total_amount": result["total_amount"],
            "agent": result["agent"],
            "reasoning": result.get("reasoning", ""),
            "order_id": order_id,
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
