# Quick Start: Agentic Barista

## 🚀 Get Started in 3 Steps

### Step 1: Seed Menu Data
```bash
cd backend
python -m apps.agentic_barista.seed_menu
```

Expected output:
```
✅ Seeded 10 menu items
```

### Step 2: Start Services
```bash
# Terminal 1 - Backend
cd backend
uvicorn main:app --reload

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### Step 3: Test the App
1. Open http://localhost:3000
2. Click the **"Agentic Barista"** card (orange, with ☕ icon)
3. Try these commands:

```
"Show me the menu"
"What coffee do you have?"
"Add 2 lattes"
"Add a croissant"
"Show my cart"
"Confirm order"
```

## 🎯 Example Conversation

```
You: Show me the menu

Agent [MENU]: 📋 Full Menu:

COFFEE:
• Espresso - $2.50
• Americano - $3.00
• Latte - $4.50
• Cappuccino - $4.00
• Mocha - $5.00

PASTRY:
• Croissant - $3.50
• Blueberry Muffin - $3.00
• Chocolate Chip Cookie - $2.50

FOOD:
• Avocado Toast - $6.00
• Bagel with Cream Cheese - $4.50

---

You: Add 2 lattes and 1 croissant

Agent [ORDER]: ✅ Added to cart:
• 2x Latte ($4.50 each)
• 1x Croissant ($3.50 each)

Say 'show cart' to see your total!

---

You: Show my cart

Agent [ORDER]: 🛒 Your Cart:

• 2x Latte - $9.00
• 1x Croissant - $3.50

Total: $12.50

Say 'confirm order' to complete your purchase!

---

You: Confirm order

Agent [CONFIRMATION]: ✅ Order Confirmed! (Order #1)

Items:
• 2x Latte - $9.00
• 1x Croissant - $3.50

Total: $12.50

Your order will be ready in 10-15 minutes. Thank you! ☕
```

## 🔧 Switch AI Models

Use the dropdown in the top-right to switch between:
- **Gemini 2.0 Flash** (default, fastest)
- **Gemini 1.5 Flash** (balanced)
- **Llama 3.3 70B** (via Groq)
- **Nova Lite** (AWS Bedrock)

## 🧪 Test Without UI

```bash
cd backend
python test_barista.py
```

## 📊 Check Orders

```bash
curl http://localhost:8000/api/apps/agentic-barista/orders/test_session
```

## 🐛 Troubleshooting

**Menu is empty?**
```bash
python -m apps.agentic_barista.seed_menu
```

**Backend won't start?**
- Check DATABASE_URL in .env
- Ensure PostgreSQL is running

**Frontend shows error?**
- Check NEXT_PUBLIC_API_URL in .env
- Ensure backend is running on port 8000

## 🎨 Features to Try

1. **Browse by Category**: "Show me coffee" or "What pastries do you have?"
2. **Add Multiple Items**: "Add 3 lattes and 2 muffins"
3. **Remove Items**: "Remove the croissant"
4. **Check Total**: "Show my cart" or "What's my total?"
5. **Complete Order**: "Confirm order" or "Place my order"

## 📱 UI Features

- **Cart Badge**: Shows item count in top-right
- **Agent Labels**: See which agent is responding
- **Live Total**: Updates as you add items
- **Model Selector**: Switch AI models on the fly
- **Timestamps**: See when each message was sent

## 🚀 Ready for Production

The app is already integrated with:
- ✅ Your existing database
- ✅ Your authentication system
- ✅ Your Docker setup
- ✅ Your Kubernetes manifests

Just deploy as usual!

## 📚 Learn More

- Full docs: `backend/apps/agentic_barista/README.md`
- Implementation details: `AGENTIC_BARISTA_IMPLEMENTATION.md`
- Main README: `README.md`

---

**Enjoy your AI-powered coffee ordering! ☕🤖**
