# Co-Intelligence - Quick Start Guide

## Prerequisites (Do Once)

### 1. Copy and configure .env file
```bash
cp .env.example .env
# Edit .env with your AWS credentials and API keys
```

### 2. Deploy CloudFormation Stack
```bash
cd infrastructure
aws cloudformation create-stack \
  --stack-name co-intelligence \
  --template-body file://cloudformation.yaml \
  --parameters ParameterKey=DBUsername,ParameterValue=cointelligence \
               ParameterKey=DBPassword,ParameterValue=SecurePass123! \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region us-east-1

# Wait for completion (10-15 minutes)
aws cloudformation wait stack-create-complete --stack-name co-intelligence --region us-east-1
```

---

## Deploy Application (Automated)

```bash
./deploy.sh
```

**That's it!** The script will:
- Configure RDS and verify availability
- Build Docker images
- Push to ECR
- Create Kubernetes secrets
- Deploy backend and frontend to EKS
- Set up LoadBalancers
- Display access URLs

**Time:** ~12-15 minutes

---

## Daily Usage

### Check Status
```bash
./status.sh
```

### View Logs
```bash
./logs.sh backend   # View backend logs
./logs.sh frontend  # View frontend logs
```

### Update Backend (after code changes)
```bash
./update-backend.sh
```

### Update Frontend (after code changes)
```bash
./update-frontend.sh
```

---

## Testing AI Chat

### 1. Basic Chat
1. Login to the application
2. Click **"AI Chat"** card
3. Try: "Hello, can you help me with Python?"
4. Switch models using the dropdown (Gemini, Groq, Bedrock)

### 2. Code Execution
1. Ask: "What's 15% of 2847?"
2. **Expected:** AI executes code and shows result
3. Try: "Generate first 10 Fibonacci numbers"
4. **Expected:** Code execution with output

### 3. Document Upload
1. Start a chat session (send a message first)
2. Click the 📎 upload button (becomes active after first message)
3. Upload a PDF, DOCX, TXT, or MD file
4. Ask: "What's in the document?"
5. **Expected:** AI responds using document content

### 4. Web Search (Optional)
1. Get Tavily API key from https://tavily.com/
2. Add to `.env`: `TAVILY_API_KEY=tvly-your-key`
3. Update secrets and restart backend:
   ```bash
   kubectl delete secret app-secrets
   kubectl create secret generic app-secrets --from-env-file=.env
   kubectl rollout restart deployment/backend
   ```
4. Enable web search toggle in UI
5. Ask: "What's the latest news about AI?"
6. **Expected:** AI searches web and provides current information

---

## Testing Agentic Barista

### 1. Seed Menu Data (First Time Only)
```bash
cd backend
python -m apps.agentic_barista.seed_menu
```

### 2. Test the App
1. Login to the application
2. Click **"Agentic Barista"** card (orange, with ☕ icon)
3. Click the floating chat button (bottom-right)

### 3. Example Conversation
```
You: Show me the menu

AI [MENU AGENT]: 📋 Full Menu:
COFFEE: Espresso ($2.50), Latte ($4.50), Cappuccino ($4.00)...

---

You: Add 2 lattes and 1 croissant

AI [ORDER AGENT]: ✅ Added to cart:
• 2x Latte ($4.50 each)
• 1x Croissant ($3.50 each)

---

You: Show my cart

AI [ORDER AGENT]: 🛒 Your Cart:
• 2x Latte - $9.00
• 1x Croissant - $3.50
Total: $12.50

---

You: Confirm order

AI [CONFIRMATION AGENT]: ✅ Order Confirmed! (Order #1)
Total: $12.50
Your order will be ready in 10-15 minutes!

---

You: Why do people love coffee?

AI [GENERAL]: People love coffee for its rich aroma, comforting 
warmth, and energizing caffeine boost. It's also a beloved ritual!
```

### 4. Features to Try
- **Browse by Category**: "Show me coffee" or "What pastries do you have?"
- **Add Multiple Items**: "Add 3 lattes and 2 muffins"
- **Remove Items**: "Remove the croissant"
- **Check Total**: "Show my cart" or "What's my total?"
- **General Questions**: "Why do people love coffee?" (AI reasoning)
- **Complete Order**: "Confirm order" or "Place my order"

---

## Verification Commands

### Check Deployment Status
```bash
kubectl get pods
kubectl get svc
```

### Check Backend Logs
```bash
kubectl logs deployment/backend --tail=50
```

### Check Frontend Logs
```bash
kubectl logs deployment/frontend --tail=50
```

### Verify Lambda (Code Execution)
```bash
aws lambda get-function --function-name co-intelligence-code-executor --region us-east-1
```

### Check Orders (Barista)
```bash
curl http://<BACKEND_URL>:8000/api/apps/agentic-barista/orders/test_session
```

---

## Common Issues & Solutions

### Issue: 401 Unauthorized errors
**Solution:** 
- Make sure you're logged in
- Token expires after 30 minutes - login again
- Check if token is in localStorage (F12 → Application → Local Storage)

### Issue: Upload button disabled
**Solution:**
- Send a message first to create a session
- Upload only works within an active session

### Issue: Web search not working
**Solution:**
- Get Tavily API key from https://tavily.com/
- Add to `.env` and update Kubernetes secret
- Restart backend deployment

### Issue: Code execution not working
**Solution:**
- Verify you're using **Gemini** model (only model with function calling)
- Check Lambda exists: `aws lambda get-function --function-name co-intelligence-code-executor`
- Check backend logs for errors

### Issue: Barista menu is empty
**Solution:**
```bash
cd backend
python -m apps.agentic_barista.seed_menu
```

### Issue: Backend won't start
**Solution:**
- Check DATABASE_URL in .env
- Verify RDS is available
- Check pod logs: `kubectl logs deployment/backend`

---

## Success Criteria

✅ **AI Chat:**
- Chat responds correctly (no 401 errors)
- Code execution works (Gemini model)
- Upload button has clear visual feedback
- Documents can be uploaded and queried
- Web search works (with API key)

✅ **Agentic Barista:**
- Menu displays correctly
- Can add/remove items from cart
- Cart total updates correctly
- Orders can be confirmed
- AI reasoning handles general questions
- Agent labels show correctly (MENU, ORDER, CONFIRMATION, GENERAL)

---

## Next Steps

1. **Explore Features**: Try all AI Chat and Barista features
2. **Add API Keys**: Get Tavily key for web search (optional)
3. **Review Documentation**: 
   - [AI_CHAT.md](AI_CHAT.md) - AI Chat features
   - [CODE_EXECUTION.md](CODE_EXECUTION.md) - Code execution details
   - `backend/apps/agentic_barista/README.md` - Barista architecture
4. **Monitor Logs**: Watch for any issues
5. **Scale**: Adjust HPA settings if needed

---

## Support

If you encounter any issues:
1. Check browser console (F12)
2. Review backend logs: `kubectl logs deployment/backend`
3. Verify you're logged in
4. Clear cache and try again
5. Check CloudFormation stack status
6. Verify all pods are running: `kubectl get pods`

---

**Enjoy your AI-powered platform! 🚀**
