# Co-Intelligence V1.0 Beta

**Where Human Meets AI Intelligence**

A multi-AI chat application with FastAPI backend, Next.js frontend, deployed on AWS EKS.

## Architecture

- **Backend**: FastAPI + Tortoise ORM + LangGraph 1.0.1
- **Frontend**: Next.js 14 (App Router)
- **Database**: AWS RDS PostgreSQL
- **AI Models**: Gemini 2.5 Flash Lite, Groq Mixtral, AWS Bedrock Nova
- **Code Execution**: AWS Lambda (autonomous Python execution)
- **Infrastructure**: AWS EKS (t3.medium), ECR, S3, Lambda
- **Region**: us-east-1

## Applications

### 1. AI Chat
- 🤖 **Multi-AI Chat** - Switch between Gemini, Groq, and Bedrock models
- 📄 **Document Upload** - PDF, DOCX, TXT support with text extraction
- 🌐 **Web Search** - Real-time internet search (Tavily integration)
- ⚡ **Code Execution** - AI automatically runs Python code when needed
- 💬 **Streaming Responses** - Real-time AI responses

### 2. Agentic Barista
- ☕ **LangGraph Workflow** - Multi-agent system with state management
- 🤖 **3 Specialized Agents** - Menu, Order, and Confirmation agents
- 🛒 **Cart Management** - Add/remove items, view totals
- 📋 **Menu Discovery** - Browse coffee, pastries, and food items
- ✅ **Order Confirmation** - Complete orders with database persistence

## Platform Features

- 🔐 **Secure Authentication** - JWT-based user authentication
- ☁️ **Cloud Native** - Deployed on AWS EKS with auto-scaling
- 🧩 **Modular Architecture** - Easy to add new AI applications

## Prerequisites

- AWS CLI configured
- Docker installed
- kubectl installed
- Node.js 20+
- Python 3.11+

## Setup Instructions

### 1. Deploy AWS Infrastructure

```bash
cd infrastructure

# Deploy CloudFormation stack
aws cloudformation create-stack \
  --stack-name co-intelligence \
  --template-body file://cloudformation.yaml \
  --parameters ParameterKey=DBUsername,ParameterValue=cointelligence \
               ParameterKey=DBPassword,ParameterValue=YourSecurePassword123 \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region us-east-1

# Wait for stack creation
aws cloudformation wait stack-create-complete \
  --stack-name co-intelligence \
  --region us-east-1

# Get outputs
aws cloudformation describe-stacks \
  --stack-name co-intelligence \
  --region us-east-1 \
  --query 'Stacks[0].Outputs'
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in values from CloudFormation outputs:

```bash
cp .env.example .env
# Edit .env with your values
```

### 3. Build and Push Docker Images

```bash
# Get AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Build and push backend
cd backend
docker build -t co-intelligence-backend .
docker tag co-intelligence-backend:latest $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/co-intelligence-backend:latest
docker push $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/co-intelligence-backend:latest

# Build and push frontend
cd ../frontend
docker build -t co-intelligence-frontend .
docker tag co-intelligence-frontend:latest $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/co-intelligence-frontend:latest
docker push $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/co-intelligence-frontend:latest
```

### 4. Deploy to EKS

```bash
# Update kubeconfig
aws eks update-kubeconfig --name co-intelligence-cluster --region us-east-1

# Update K8s manifests with your account ID
cd ../k8s
sed -i "s/<ACCOUNT_ID>/$ACCOUNT_ID/g" backend-deployment.yaml
sed -i "s/<ACCOUNT_ID>/$ACCOUNT_ID/g" frontend-deployment.yaml

# Create secrets (copy template and fill values)
cp secrets.yaml.template secrets.yaml
# Edit secrets.yaml with your actual values

# Apply manifests
kubectl apply -f secrets.yaml
kubectl apply -f backend-deployment.yaml
kubectl apply -f backend-service.yaml
kubectl apply -f frontend-deployment.yaml
kubectl apply -f frontend-service.yaml

# Get LoadBalancer URL
kubectl get svc frontend -w
```

### 5. Local Development

```bash
# Start local environment
docker-compose up

# Backend: http://localhost:8000
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/me` - Get current user

### AI Chat
- `POST /api/apps/ai-chat/sessions` - Create chat session
- `GET /api/apps/ai-chat/sessions` - List sessions
- `GET /api/apps/ai-chat/sessions/{id}/messages` - Get messages
- `POST /api/apps/ai-chat/chat` - Send message

### Agentic Barista
- `POST /api/apps/agentic-barista/chat` - Chat with barista agent
- `GET /api/apps/agentic-barista/menu` - Get menu items
- `GET /api/apps/agentic-barista/orders/{session_id}` - Get order history

## Scaling

- **Node Group**: Auto-scales from 1 to 3 t3.medium instances
- **Pods**: HPA scales backend/frontend from 1 to 3 replicas at 70% CPU

## Monitoring

```bash
# Check pod status
kubectl get pods

# View logs
kubectl logs -f deployment/backend
kubectl logs -f deployment/frontend

# Check HPA status
kubectl get hpa
```

## Cleanup

```bash
# Delete K8s resources
kubectl delete -f k8s/

# Delete CloudFormation stack
aws cloudformation delete-stack --stack-name co-intelligence --region us-east-1
```

## Adding New Apps

1. Create new app directory in `backend/apps/`
2. Add models, routes, and logic
3. Register router in `backend/main.py`
4. Add frontend page in `frontend/app/apps/`
5. Add card to homepage

## License

MIT
