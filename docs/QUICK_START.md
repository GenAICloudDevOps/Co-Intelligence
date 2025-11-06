# Co-Intelligence - Quick Start Guide

## Common Setup Steps (Required for Both Options)

### Step 1: Configure Environment
```bash
cp .env.example .env
# Edit .env with your AWS credentials and API keys
```

### Step 2: Deploy CloudFormation Stack
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

### Step 3: Create EKS Cluster
```bash
# Option A: AWS Console (Recommended)
1. Go to AWS Console → EKS → Create cluster
2. Name: co-intelligence-cluster
3. Kubernetes version: 1.28 or later
4. Use default VPC or select your VPC
5. Select 2+ subnets in different AZs
6. Create cluster (10-15 minutes)

# Option B: AWS CLI
aws eks create-cluster \
  --name co-intelligence-cluster \
  --role-arn <EKS_CLUSTER_ROLE_ARN> \
  --resources-vpc-config subnetIds=<SUBNET_IDS>,securityGroupIds=<SG_IDS> \
  --region us-east-1

aws eks wait cluster-active --name co-intelligence-cluster --region us-east-1
```

### Step 4: Create Node Group
```bash
# Option A: AWS Console (Recommended)
1. Go to Cluster → Compute → Add node group
2. Name: co-intelligence-nodes
3. Node IAM role: Select the role created by CloudFormation
4. Instance type: t3.medium
5. Scaling: Min=1, Max=3, Desired=1
6. Create (5-10 minutes)

# Option B: AWS CLI
aws eks create-nodegroup \
  --cluster-name co-intelligence-cluster \
  --nodegroup-name co-intelligence-nodes \
  --node-role <NODE_ROLE_ARN> \
  --subnets <SUBNET_IDS> \
  --instance-types t3.medium \
  --scaling-config minSize=1,maxSize=3,desiredSize=1 \
  --region us-east-1

aws eks wait nodegroup-active \
  --cluster-name co-intelligence-cluster \
  --nodegroup-name co-intelligence-nodes \
  --region us-east-1
```

### Step 5: Configure kubectl
```bash
aws eks update-kubeconfig --name co-intelligence-cluster --region us-east-1

# Verify connection
kubectl get nodes
```

---

## Option 1: Automated Deployment (Recommended)

**One command to deploy everything:**

```bash
./deploy.sh
```

**What it does:**
- Verifies CloudFormation stack and RDS availability
- Logs into ECR
- Builds and pushes backend Docker image
- Builds and pushes frontend Docker image
- Creates Kubernetes secrets
- Deploys backend to EKS
- Deploys frontend to EKS
- Sets up LoadBalancers
- Waits for health checks
- Displays access URLs

**Time:** ~12-15 minutes

**Output:**
```
🎉 Deployment Complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Frontend: http://<FRONTEND_URL>
Backend:  http://<BACKEND_URL>:8000
```

---

## Option 2: Manual Deployment

### Step 1: Get CloudFormation Outputs
```bash
aws cloudformation describe-stacks \
  --stack-name co-intelligence \
  --region us-east-1 \
  --query 'Stacks[0].Outputs'
```

Note the values for:
- RDSEndpoint
- BackendECRUri
- FrontendECRUri

### Step 2: Login to ECR
```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
```

### Step 3: Build and Push Backend
```bash
cd backend
docker build -t co-intelligence-backend .
docker tag co-intelligence-backend:latest $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/co-intelligence-backend:latest
docker push $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/co-intelligence-backend:latest
cd ..
```

### Step 4: Create Kubernetes Secrets
```bash
# Update secrets.yaml with your values
cp k8s/secrets.yaml.template k8s/secrets.yaml
# Edit k8s/secrets.yaml with actual credentials

kubectl apply -f k8s/secrets.yaml
```

### Step 5: Deploy Backend
```bash
# Update backend deployment with your account ID
sed -i "s/<ACCOUNT_ID>/$ACCOUNT_ID/g" k8s/backend-deployment.yaml

kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml

# Wait for LoadBalancer
kubectl get svc backend -w
# Press Ctrl+C when EXTERNAL-IP appears
```

### Step 6: Get Backend URL
```bash
BACKEND_URL=$(kubectl get svc backend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "Backend URL: http://$BACKEND_URL:8000"

# Wait for backend to be healthy
sleep 30
curl http://$BACKEND_URL:8000/health
```

### Step 7: Build and Push Frontend
```bash
cd frontend
docker build --build-arg NEXT_PUBLIC_API_URL=http://$BACKEND_URL:8000 -t co-intelligence-frontend .
docker tag co-intelligence-frontend:latest $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/co-intelligence-frontend:latest
docker push $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/co-intelligence-frontend:latest
cd ..
```

### Step 8: Deploy Frontend
```bash
# Update frontend deployment with your account ID
sed -i "s/<ACCOUNT_ID>/$ACCOUNT_ID/g" k8s/frontend-deployment.yaml

kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/frontend-service.yaml

# Wait for LoadBalancer
kubectl get svc frontend -w
# Press Ctrl+C when EXTERNAL-IP appears
```

### Step 9: Get Frontend URL
```bash
FRONTEND_URL=$(kubectl get svc frontend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "Frontend URL: http://$FRONTEND_URL"
```

### Step 10: Verify Deployment
```bash
kubectl get pods
kubectl get svc
```

---

## Post-Deployment: Seed Barista Menu

```bash
# Get backend pod name
BACKEND_POD=$(kubectl get pods -l app=backend -o jsonpath='{.items[0].metadata.name}')

# Seed menu data
kubectl exec -it $BACKEND_POD -- python -m apps.agentic_barista.seed_menu
```

Expected output:
```
✅ Seeded 10 menu items
```

---

## Testing AI Chat

### 1. Basic Chat
1. Open the frontend URL in your browser
2. Register/Login
3. Click **"AI Chat"** card
4. Try: "Hello, can you help me with Python?"
5. Switch models using the dropdown (Gemini, Groq, Bedrock)

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

### 1. Access the App
1. Login to the application
2. Click **"Agentic Barista"** card (orange, with ☕ icon)
3. Click the floating chat button (bottom-right)

### 2. Example Conversation
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

### 3. Features to Try
- **Browse by Category**: "Show me coffee" or "What pastries do you have?"
- **Add Multiple Items**: "Add 3 lattes and 2 muffins"
- **Remove Items**: "Remove the croissant"
- **Check Total**: "Show my cart" or "What's my total?"
- **General Questions**: "Why do people love coffee?" (AI reasoning)
- **Complete Order**: "Confirm order" or "Place my order"

---

## Daily Usage Commands

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
BACKEND_URL=$(kubectl get svc backend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
curl http://$BACKEND_URL:8000/api/apps/agentic-barista/orders/test_session
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
BACKEND_POD=$(kubectl get pods -l app=backend -o jsonpath='{.items[0].metadata.name}')
kubectl exec -it $BACKEND_POD -- python -m apps.agentic_barista.seed_menu
```

### Issue: Backend won't start
**Solution:**
- Check DATABASE_URL in secrets
- Verify RDS is available
- Check pod logs: `kubectl logs deployment/backend`

### Issue: Pods stuck in Pending
**Solution:**
- Check node group is active: `kubectl get nodes`
- Verify nodes have capacity: `kubectl describe nodes`
- Check pod events: `kubectl describe pod <POD_NAME>`

---

## Success Criteria

✅ **Infrastructure:**
- CloudFormation stack created
- EKS cluster active
- Node group running
- kubectl connected

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
   - `../backend/apps/agentic_barista/README.md` - Barista architecture
4. **Monitor Logs**: Watch for any issues
5. **Scale**: Adjust HPA settings if needed

---

## Time Estimates

**Common Setup:**
- CloudFormation: 10-15 minutes
- EKS Cluster: 10-15 minutes
- Node Group: 5-10 minutes
- **Total: 25-40 minutes**

**Automated Deployment:**
- deploy.sh: 12-15 minutes

**Manual Deployment:**
- Docker builds + pushes: 8-10 minutes
- Kubernetes deployment: 5-7 minutes
- **Total: 13-17 minutes**

**Grand Total: 38-57 minutes** (first time setup)

---

**Enjoy your AI-powered platform! 🚀**
