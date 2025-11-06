# Agentic Barista

AI-powered coffee ordering system using LangGraph 1.0.1 multi-agent workflow.

## Architecture

### Multi-Agent System
- **MenuAgent**: Handles menu queries and browsing
- **OrderAgent**: Manages cart operations (add/remove items)
- **ConfirmationAgent**: Processes order confirmation and saves to database
- **Coordinator**: LangGraph StateGraph that routes messages to appropriate agents

### Technology Stack
- **LangGraph 1.0.1**: State machine workflow
- **Tortoise ORM**: Database models
- **FastAPI**: REST API endpoints
- **Multi-Model Support**: Gemini, Groq, Bedrock

## Database Models

### MenuItem
- name, description, price, category, available
- Categories: coffee, pastry, food

### Order
- session_id, user_id, items (JSON), total, status, created_at

## API Endpoints

### POST /api/apps/agentic-barista/chat
Chat with the barista agent.

**Request:**
```json
{
  "message": "Show me the menu",
  "session_id": "abc123",
  "model": "gemini-2.0-flash-exp"
}
```

**Response:**
```json
{
  "response": "Menu text...",
  "cart": {"1": 2, "3": 1},
  "total_amount": 12.50,
  "agent": "menu",
  "session_id": "abc123"
}
```

### GET /api/apps/agentic-barista/menu
Get all available menu items.

### GET /api/apps/agentic-barista/orders/{session_id}
Get order history for a session.

## Setup

1. **Seed Menu Data:**
```bash
cd backend
python -m apps.agentic_barista.seed_menu
```

2. **Database Migration:**
Tables are auto-created on first run via Tortoise ORM.

3. **Test the API:**
```bash
curl -X POST http://localhost:8000/api/apps/agentic-barista/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "show menu", "session_id": "test123"}'
```

## Workflow Flow

```
User Message
    ↓
Coordinator (Router Node)
    ↓
Detect Intent
    ↓
Route to Agent:
  - "menu" → MenuAgent
  - "add/cart" → OrderAgent
  - "confirm" → ConfirmationAgent
    ↓
Agent Processes Message
    ↓
Update State (cart, total)
    ↓
Return Response
```

## Example Conversations

**Browse Menu:**
```
User: "Show me the menu"
Agent: [MenuAgent] Lists all items with prices

User: "What coffee do you have?"
Agent: [MenuAgent] Lists coffee items only
```

**Order Items:**
```
User: "Add 2 lattes"
Agent: [OrderAgent] ✅ Added to cart: 2x Latte ($4.50 each)

User: "Show my cart"
Agent: [OrderAgent] 🛒 Your Cart: 2x Latte - $9.00, Total: $9.00
```

**Confirm Order:**
```
User: "Confirm order"
Agent: [ConfirmationAgent] ✅ Order Confirmed! (Order #123)
```

## State Management

The `CafeState` maintains:
- `messages`: Conversation history
- `session_id`: User session identifier
- `cart`: Dict of item_id → quantity
- `current_agent`: Which agent is handling the message
- `total_amount`: Current cart total

Cart persists in memory across messages until order is confirmed.
