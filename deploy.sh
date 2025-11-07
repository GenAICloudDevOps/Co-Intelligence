#!/bin/bash
set -e

echo "🚀 Co-Intelligence Deployment"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Load environment variables
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    exit 1
fi
source .env

# Validate required variables
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ] || [ -z "$AWS_REGION" ]; then
    echo "❌ AWS credentials not found in .env"
    exit 1
fi

export AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_REGION
STACK_NAME=${STACK_NAME:-co-intelligence}
EKS_CLUSTER_NAME=${EKS_CLUSTER_NAME:-co-intelligence-cluster}

echo "✓ Loaded configuration"

# Get CloudFormation outputs
echo "📋 Getting CloudFormation outputs..."
RDS_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`RDSEndpoint`].OutputValue' \
    --output text)

ECR_BACKEND=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`BackendECRUri`].OutputValue' \
    --output text)

ECR_FRONTEND=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`FrontendECRUri`].OutputValue' \
    --output text)

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "✓ RDS Endpoint: $RDS_ENDPOINT"
echo "✓ ECR Backend: $ECR_BACKEND"
echo "✓ ECR Frontend: $ECR_FRONTEND"

# Verify RDS is available
echo ""
echo "🗄️  Verifying RDS..."
DB_INSTANCE_ID=$(aws rds describe-db-instances \
    --region $AWS_REGION \
    --query 'DBInstances[?Endpoint.Address==`'$RDS_ENDPOINT'`].DBInstanceIdentifier' \
    --output text)

aws rds wait db-instance-available \
    --db-instance-identifier $DB_INSTANCE_ID \
    --region $AWS_REGION

echo "✓ RDS ready"

# Configure kubectl
echo ""
echo "☸️  Configuring kubectl..."
aws eks update-kubeconfig \
    --name $EKS_CLUSTER_NAME \
    --region $AWS_REGION

kubectl get nodes > /dev/null
echo "✓ Connected to EKS cluster"

# Login to ECR
echo ""
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
echo "✓ ECR login successful"

# Build and push backend
echo ""
echo "🔨 Building backend image..."
cd backend
docker build -t co-intelligence-backend . > /dev/null
docker tag co-intelligence-backend:latest $ECR_BACKEND:latest
echo "✓ Backend image built"

echo "📤 Pushing backend image..."
docker push $ECR_BACKEND:latest > /dev/null
echo "✓ Backend image pushed"
cd ..

# Create Kubernetes secrets
echo ""
echo "🔑 Creating Kubernetes secrets..."
DB_PASSWORD_ENCODED=$(echo -n "${DB_PASSWORD}" | sed 's/!/\\%21/g')
DATABASE_URL="postgres://${DB_USERNAME}:${DB_PASSWORD_ENCODED}@${RDS_ENDPOINT}:5432/postgres?ssl=require"

kubectl create secret generic app-secrets \
    --from-literal=DATABASE_URL="$DATABASE_URL" \
    --from-literal=SECRET_KEY="${SECRET_KEY}" \
    --from-literal=GEMINI_API_KEY="${GEMINI_API_KEY:-}" \
    --from-literal=GROQ_API_KEY="${GROQ_API_KEY:-}" \
    --from-literal=AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}" \
    --from-literal=AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}" \
    --from-literal=AWS_REGION="${AWS_REGION}" \
    --dry-run=client -o yaml | kubectl apply -f -

echo "✓ Secrets created"

# Deploy backend
echo ""
echo "🚀 Deploying backend..."
sed "s|<ACCOUNT_ID>|$ACCOUNT_ID|g" k8s/backend-deployment.yaml | kubectl apply -f -
kubectl apply -f k8s/backend-service.yaml
kubectl patch svc backend -p '{"spec":{"type":"LoadBalancer"}}' > /dev/null 2>&1 || true

echo "⏳ Waiting for backend LoadBalancer (2-3 min)..."
while true; do
    BACKEND_URL=$(kubectl get svc backend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
    if [ ! -z "$BACKEND_URL" ]; then
        break
    fi
    sleep 5
done

echo "✓ Backend deployed at: http://$BACKEND_URL:8000"

# Wait for backend to be healthy
echo "⏳ Waiting for backend to be healthy..."
sleep 30
for i in {1..30}; do
    if curl -s http://$BACKEND_URL:8000/health > /dev/null 2>&1; then
        echo "✓ Backend is healthy"
        break
    fi
    sleep 5
done

# Update .env with backend URL
echo ""
echo "🔧 Updating .env with backend URL..."
sed -i.bak "s|NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=http://$BACKEND_URL:8000|" .env
echo "✓ .env updated"

# Build and push frontend
echo ""
echo "🔨 Building frontend image..."
cd frontend
docker build --build-arg NEXT_PUBLIC_API_URL=http://$BACKEND_URL:8000 -t co-intelligence-frontend . > /dev/null
docker tag co-intelligence-frontend:latest $ECR_FRONTEND:latest
echo "✓ Frontend image built"

echo "📤 Pushing frontend image..."
docker push $ECR_FRONTEND:latest > /dev/null
echo "✓ Frontend image pushed"
cd ..

# Deploy frontend
echo ""
echo "🚀 Deploying frontend..."
sed -e "s|<ACCOUNT_ID>|$ACCOUNT_ID|g" \
    -e "s|value: \".*\"|value: \"http://$BACKEND_URL:8000\"|" \
    k8s/frontend-deployment.yaml | kubectl apply -f -
kubectl apply -f k8s/frontend-service.yaml

echo "⏳ Waiting for frontend LoadBalancer (2-3 min)..."
while true; do
    FRONTEND_URL=$(kubectl get svc frontend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
    if [ ! -z "$FRONTEND_URL" ]; then
        break
    fi
    sleep 5
done

echo "✓ Frontend deployed at: http://$FRONTEND_URL"

# Verify deployment
echo ""
echo "✅ Verifying deployment..."
kubectl get pods
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Deployment Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Frontend: http://$FRONTEND_URL"
echo "Backend:  http://$BACKEND_URL:8000"
echo ""
echo "Next steps:"
echo "1. Open http://$FRONTEND_URL in your browser"
echo "2. Click 'Register' to create an account"
echo "3. Launch AI Chat and start chatting!"
echo ""
