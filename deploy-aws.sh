#!/bin/bash
set -e

echo "=========================================="
echo "Co-Intelligence AWS Deployment"
echo "=========================================="

command -v aws >/dev/null 2>&1 || { echo "AWS CLI required"; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "kubectl required"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "docker required"; exit 1; }

STACK_NAME=${STACK_NAME:-co-intelligence}
EKS_CLUSTER_NAME=${EKS_CLUSTER_NAME:-co-intelligence-cluster}
IMAGE_TAG=${IMAGE_TAG:-$(date +%Y%m%d%H%M%S)}

# Load API keys from .env
if [ -f ".env" ]; then
    echo "Loading from .env..."
    export $(grep -E '^(GEMINI_API_KEY|GROQ_API_KEY|TAVILY_API_KEY|TINKER_API_KEY|AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|AWS_REGION|DB_USERNAME|TINKER_BASE_PATH)=' .env | xargs)
fi

AWS_REGION=${AWS_REGION:-us-east-1}
DB_USERNAME=${DB_USERNAME:-cointelligence}

# Validate AWS credentials
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "Error: AWS credentials not configured"
    echo "Run 'aws configure' or set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY in .env"
    exit 1
fi

export AWS_REGION
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "✓ AWS Account: $ACCOUNT_ID"

# Get CloudFormation outputs
echo "Fetching CloudFormation outputs..."
RDS_ENDPOINT=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`RDSEndpoint`].OutputValue' --output text)
ECR_BACKEND=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`BackendECRUri`].OutputValue' --output text)
ECR_FRONTEND=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`FrontendECRUri`].OutputValue' --output text)
S3_BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`S3BucketName`].OutputValue' --output text)
LAMBDA_ARN=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`CodeExecutorLambdaArn`].OutputValue' --output text)

# Fetch secrets
echo "Fetching secrets..."
SECRETS_JSON=$(aws secretsmanager get-secret-value --secret-id co-intelligence-secrets --region $AWS_REGION --query SecretString --output text)
DB_PASSWORD=$(echo $SECRETS_JSON | jq -r '.password // .DB_PASSWORD')
SECRET_KEY=$(aws secretsmanager get-secret-value --secret-id co-intelligence-secret-key --region $AWS_REGION --query SecretString --output text)

echo "✓ Infrastructure values retrieved"

# Update .env
echo "Updating .env..."
cat > .env << EOF
# AI API Keys
GEMINI_API_KEY=${GEMINI_API_KEY:-}
GROQ_API_KEY=${GROQ_API_KEY:-}
TAVILY_API_KEY=${TAVILY_API_KEY:-}
TINKER_API_KEY=${TINKER_API_KEY:-}

# AWS Credentials
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID:-}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-}
AWS_REGION=$AWS_REGION

# Infrastructure (auto-populated)
DATABASE_URL=postgres://$DB_USERNAME:$DB_PASSWORD@$RDS_ENDPOINT:5432/postgres?sslmode=require
SECRET_KEY=$SECRET_KEY
S3_BUCKET_NAME=$S3_BUCKET_NAME
CODE_EXECUTOR_URL=$LAMBDA_ARN
# CORS / API surface (comma-separated, e.g., https://app.example.com,https://admin.example.com)
CORS_ALLOW_ORIGINS=${CORS_ALLOW_ORIGINS:-}
# Leave true for dev; set false and run migrations in prod
AUTO_GENERATE_SCHEMAS=${AUTO_GENERATE_SCHEMAS:-true}
# Tinker assets base path (container default)
TINKER_BASE_PATH=${TINKER_BASE_PATH:-/app}
EOF
echo "✓ .env updated"

# Configure kubectl
echo "Configuring kubectl for EKS..."
aws eks update-kubeconfig --name $EKS_CLUSTER_NAME --region $AWS_REGION
echo "✓ kubectl configured"

# Apply IRSA service account and observability DaemonSet
echo "Applying IRSA service account and X-Ray daemonset..."
kubectl apply -f k8s/sa-backend-irsa.yaml
kubectl apply -f k8s/xray-daemonset.yaml

# Login to ECR
echo "Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
echo "✓ ECR login successful"

# Build and push images
echo "Building and pushing backend..."
docker build -t $ECR_BACKEND:$IMAGE_TAG ./backend
docker push $ECR_BACKEND:$IMAGE_TAG

# Deploy backend first to get LB hostname
echo "Deploying backend..."
sed -e "s|<ACCOUNT_ID>|$ACCOUNT_ID|g" -e "s|<IMAGE_TAG>|$IMAGE_TAG|g" k8s/backend-deployment.yaml | kubectl apply -f -
kubectl apply -f k8s/backend-service.yaml
echo "✓ Backend applied"

# Wait for backend LoadBalancer hostname (for frontend API URL)
echo "Waiting for backend LoadBalancer..."
BACKEND_LB=""
for i in {1..30}; do
    BACKEND_LB=$(kubectl get svc backend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
    if [ -n "$BACKEND_LB" ]; then break; fi
    sleep 10
done
if [ -n "$BACKEND_LB" ]; then
    echo "✓ Backend LB: http://$BACKEND_LB"
else
    echo "⚠ Backend LB hostname not found yet; frontend API URL may need to be set manually."
fi

# Use empty NEXT_PUBLIC_API_URL so browser uses relative /api/* paths
# Next.js rewrites will proxy to backend via BACKEND_URL env var at runtime
echo "Building frontend with empty NEXT_PUBLIC_API_URL (uses Next.js rewrites)..."
docker build --build-arg NEXT_PUBLIC_API_URL="" -t $ECR_FRONTEND:$IMAGE_TAG ./frontend
docker push $ECR_FRONTEND:$IMAGE_TAG
echo "✓ Images pushed with tag $IMAGE_TAG"

# Create secrets
echo "Creating Kubernetes secrets..."
kubectl delete secret app-secrets 2>/dev/null || true
kubectl create secret generic app-secrets \
    --from-literal=DATABASE_URL="postgres://$DB_USERNAME:$DB_PASSWORD@$RDS_ENDPOINT:5432/postgres?sslmode=require" \
    --from-literal=SECRET_KEY="$SECRET_KEY" \
    --from-literal=S3_BUCKET_NAME="$S3_BUCKET_NAME" \
    --from-literal=CODE_EXECUTOR_URL="$LAMBDA_ARN" \
    --from-literal=GEMINI_API_KEY="${GEMINI_API_KEY:-}" \
    --from-literal=GROQ_API_KEY="${GROQ_API_KEY:-}" \
    --from-literal=TAVILY_API_KEY="${TAVILY_API_KEY:-}" \
    --from-literal=TINKER_API_KEY="${TINKER_API_KEY:-}" \
    --from-literal=AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-}" \
    --from-literal=AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-}" \
    --from-literal=AWS_REGION="$AWS_REGION" \
    --from-literal=CORS_ALLOW_ORIGINS="${CORS_ALLOW_ORIGINS:-}" \
    --from-literal=AUTO_GENERATE_SCHEMAS="${AUTO_GENERATE_SCHEMAS:-true}" \
    --from-literal=TINKER_BASE_PATH="${TINKER_BASE_PATH:-/app}"
echo "✓ Secrets created"

# Update K8s manifests with image URIs
echo "Creating image pull secret..."
kubectl delete secret ecr-pull 2>/dev/null || true
kubectl create secret docker-registry ecr-pull \
  --docker-server="$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com" \
  --docker-username=AWS \
  --docker-password="$(aws ecr get-login-password --region $AWS_REGION)"
echo "✓ Image pull secret created"

echo "Deploying to EKS..."
sed -e "s|<ACCOUNT_ID>|$ACCOUNT_ID|g" -e "s|<IMAGE_TAG>|$IMAGE_TAG|g" k8s/frontend-deployment.yaml | kubectl apply -f -
kubectl apply -f k8s/frontend-service.yaml
echo "✓ Deployed"

# Wait for LoadBalancer
echo "Waiting for LoadBalancer..."
for i in {1..30}; do
    FRONTEND_URL=$(kubectl get svc frontend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
    if [ -n "$FRONTEND_URL" ]; then break; fi
    sleep 10
done
if [ -n "$FRONTEND_URL" ]; then
    echo "ℹ️  Frontend LB hostname detected: http://$FRONTEND_URL"
    echo "ℹ️  Set CORS_ALLOW_ORIGINS to match your frontend origin."
    echo "    Examples:"
    echo "      CORS_ALLOW_ORIGINS=http://$FRONTEND_URL"
    echo "      CORS_ALLOW_ORIGINS=https://app.yourdomain.com,http://localhost:3000"
    if [ -z "$CORS_ALLOW_ORIGINS" ]; then
        DEFAULT_ORIGIN="http://$FRONTEND_URL"
        echo "Auto-setting CORS_ALLOW_ORIGINS to $DEFAULT_ORIGIN and updating secret..."
        kubectl create secret generic app-secrets \
            --dry-run=client -o yaml \
            --from-literal=DATABASE_URL="postgres://$DB_USERNAME:$DB_PASSWORD@$RDS_ENDPOINT:5432/postgres?sslmode=require" \
            --from-literal=SECRET_KEY="$SECRET_KEY" \
            --from-literal=S3_BUCKET_NAME="$S3_BUCKET_NAME" \
            --from-literal=CODE_EXECUTOR_URL="$LAMBDA_ARN" \
            --from-literal=GEMINI_API_KEY="${GEMINI_API_KEY:-}" \
            --from-literal=GROQ_API_KEY="${GROQ_API_KEY:-}" \
            --from-literal=TAVILY_API_KEY="${TAVILY_API_KEY:-}" \
            --from-literal=TINKER_API_KEY="${TINKER_API_KEY:-}" \
            --from-literal=AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-}" \
            --from-literal=AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-}" \
            --from-literal=AWS_REGION="$AWS_REGION" \
            --from-literal=CORS_ALLOW_ORIGINS="$DEFAULT_ORIGIN" \
            --from-literal=AUTO_GENERATE_SCHEMAS="${AUTO_GENERATE_SCHEMAS:-true}" \
            --from-literal=TINKER_BASE_PATH="${TINKER_BASE_PATH:-/app}" \
            | kubectl apply -f -
        kubectl rollout restart deployment/backend
        echo "✓ Backend restarted with CORS_ALLOW_ORIGINS=$DEFAULT_ORIGIN"
    fi
fi

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo "Frontend: http://$FRONTEND_URL"
echo ""
echo "Commands:"
echo "  kubectl get pods"
echo "  kubectl logs -f deployment/backend"
