#!/bin/bash
set -e

echo "=========================================="
echo "Co-Intelligence AWS Deployment"
echo "=========================================="

command -v aws >/dev/null 2>&1 || { echo "AWS CLI required"; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "kubectl required"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "docker required"; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "jq required"; exit 1; }

STACK_NAME=${STACK_NAME:-co-intelligence}
EKS_CLUSTER_NAME=${EKS_CLUSTER_NAME:-co-intelligence-cluster}
IMAGE_TAG=${IMAGE_TAG:-$(date +%Y%m%d%H%M%S)}

# Load configuration from .env (optional). Do NOT `source` the file because values
# may contain shell-sensitive characters (e.g., secrets with backticks).
load_from_dotenv() {
    local dotenv_file=".env"
    [ -f "$dotenv_file" ] || return 0
    echo "Loading from .env..."
    local key val
    for key in "$@"; do
        val="$(grep -E "^${key}=" "$dotenv_file" 2>/dev/null | tail -n 1 | cut -d= -f2- || true)"
        if [ -n "${val+x}" ]; then
            export "${key}=${val}"
        fi
    done
}

load_from_dotenv \
  GEMINI_API_KEY GROQ_API_KEY TAVILY_API_KEY TINKER_API_KEY \
  AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_REGION \
  DB_USERNAME TINKER_BASE_PATH CORS_ALLOW_ORIGINS AUTO_GENERATE_SCHEMAS \
  GMAIL_SMTP_USER GMAIL_SMTP_APP_PASSWORD GMAIL_SMTP_FROM_NAME

if [ -z "${GMAIL_SMTP_USER:-}" ] || [ -z "${GMAIL_SMTP_APP_PASSWORD:-}" ]; then
  echo "⚠ Gmail SMTP env vars not set (GMAIL_SMTP_USER / GMAIL_SMTP_APP_PASSWORD). Email notifications will NOT send."
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
REDIS_ENDPOINT=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`RedisEndpoint`].OutputValue' --output text)
DATA_ANALYSIS_SFN_ARN=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`DataAnalysisStateMachineArn`].OutputValue' --output text)
DATA_ANALYSIS_ATHENA_WG=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`DataAnalysisAthenaWorkGroup`].OutputValue' --output text)
DATA_ANALYSIS_GLUE_DB=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`DataAnalysisGlueDatabase`].OutputValue' --output text)

# Fail fast if required outputs are missing (common causes: wrong STACK_NAME/AWS_REGION, stack not updated, or stack still creating)
missing_outputs=()
require_output() {
  local key="$1"
  local val="$2"
  if [ -z "${val:-}" ] || [ "${val:-}" = "None" ]; then
    missing_outputs+=("$key")
  fi
}
require_output "RDSEndpoint" "$RDS_ENDPOINT"
require_output "BackendECRUri" "$ECR_BACKEND"
require_output "FrontendECRUri" "$ECR_FRONTEND"
require_output "S3BucketName" "$S3_BUCKET_NAME"
require_output "CodeExecutorLambdaArn" "$LAMBDA_ARN"
require_output "RedisEndpoint" "$REDIS_ENDPOINT"
require_output "DataAnalysisStateMachineArn" "$DATA_ANALYSIS_SFN_ARN"
require_output "DataAnalysisAthenaWorkGroup" "$DATA_ANALYSIS_ATHENA_WG"
require_output "DataAnalysisGlueDatabase" "$DATA_ANALYSIS_GLUE_DB"

if [ ${#missing_outputs[@]} -ne 0 ]; then
  echo "Error: Missing CloudFormation outputs from stack '$STACK_NAME' in region '$AWS_REGION':"
  printf ' - %s\n' "${missing_outputs[@]}"
  echo ""
  echo "Troubleshooting:"
  echo " - Confirm STACK_NAME/AWS_REGION are correct for your deployed stack."
  echo " - If this is an older stack, update it with the latest 'infrastructure/infra.yaml' (CloudFormation update-stack)."
  echo " - If the stack is still creating/updating, wait until it completes and rerun."
  exit 1
fi

# Fetch secrets
echo "Fetching secrets..."
SECRETS_JSON=$(aws secretsmanager get-secret-value --secret-id co-intelligence-secrets --region $AWS_REGION --query SecretString --output text)
DB_PASSWORD=$(echo $SECRETS_JSON | jq -r '.password // .DB_PASSWORD')
SECRET_KEY=$(aws secretsmanager get-secret-value --secret-id co-intelligence-secret-key --region $AWS_REGION --query SecretString --output text)

echo "✓ Infrastructure values retrieved"

# Upload Glue scripts needed by Data Analysis app
if [ -n "$S3_BUCKET_NAME" ]; then
  echo "Uploading Glue scripts..."
  aws s3 cp infrastructure/glue-scripts/data-analysis-etl.py "s3://$S3_BUCKET_NAME/glue-scripts/data-analysis-etl.py" --region "$AWS_REGION" >/dev/null
  echo "✓ Glue scripts uploaded"
fi

# Update .env
echo "Updating .env..."
cat > .env << EOF
# AI API Keys
GEMINI_API_KEY=${GEMINI_API_KEY:-}
GROQ_API_KEY=${GROQ_API_KEY:-}
TAVILY_API_KEY=${TAVILY_API_KEY:-}
TINKER_API_KEY=${TINKER_API_KEY:-}

# Email notifications (Gmail SMTP)
GMAIL_SMTP_USER=${GMAIL_SMTP_USER:-}
GMAIL_SMTP_APP_PASSWORD=${GMAIL_SMTP_APP_PASSWORD:-}
GMAIL_SMTP_FROM_NAME=${GMAIL_SMTP_FROM_NAME:-Co-Intelligence}

# AWS Credentials
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID:-}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-}
AWS_REGION=$AWS_REGION

# Infrastructure (auto-populated)
DATABASE_URL=postgres://$DB_USERNAME:$DB_PASSWORD@$RDS_ENDPOINT:5432/postgres?sslmode=require
SECRET_KEY=$SECRET_KEY
S3_BUCKET_NAME=$S3_BUCKET_NAME
CODE_EXECUTOR_URL=$LAMBDA_ARN
REDIS_URL=rediss://$REDIS_ENDPOINT:6379/0
# Data Analysis (App 8)
DATA_ANALYSIS_STATE_MACHINE_ARN=$DATA_ANALYSIS_SFN_ARN
DATA_ANALYSIS_GLUE_DATABASE=${DATA_ANALYSIS_GLUE_DB:-co_intelligence_data_analysis}
DATA_ANALYSIS_ATHENA_WORKGROUP=${DATA_ANALYSIS_ATHENA_WG:-co-intelligence-data-analysis}
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

# Create secrets (before deploying workloads that envFrom these)
echo "Creating Kubernetes secrets..."
kubectl create secret generic app-secrets \
    --dry-run=client -o yaml \
    --from-literal=DATABASE_URL="postgres://$DB_USERNAME:$DB_PASSWORD@$RDS_ENDPOINT:5432/postgres?sslmode=require" \
    --from-literal=SECRET_KEY="$SECRET_KEY" \
    --from-literal=S3_BUCKET_NAME="$S3_BUCKET_NAME" \
    --from-literal=CODE_EXECUTOR_URL="$LAMBDA_ARN" \
    --from-literal=REDIS_URL="rediss://$REDIS_ENDPOINT:6379/0" \
    --from-literal=GEMINI_API_KEY="${GEMINI_API_KEY:-}" \
    --from-literal=GROQ_API_KEY="${GROQ_API_KEY:-}" \
    --from-literal=TAVILY_API_KEY="${TAVILY_API_KEY:-}" \
    --from-literal=TINKER_API_KEY="${TINKER_API_KEY:-}" \
    --from-literal=GMAIL_SMTP_USER="${GMAIL_SMTP_USER:-}" \
    --from-literal=GMAIL_SMTP_APP_PASSWORD="${GMAIL_SMTP_APP_PASSWORD:-}" \
    --from-literal=GMAIL_SMTP_FROM_NAME="${GMAIL_SMTP_FROM_NAME:-Co-Intelligence}" \
    --from-literal=AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-}" \
    --from-literal=AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-}" \
    --from-literal=AWS_REGION="$AWS_REGION" \
    --from-literal=DATA_ANALYSIS_STATE_MACHINE_ARN="$DATA_ANALYSIS_SFN_ARN" \
    --from-literal=DATA_ANALYSIS_GLUE_DATABASE="${DATA_ANALYSIS_GLUE_DB:-co_intelligence_data_analysis}" \
    --from-literal=DATA_ANALYSIS_ATHENA_WORKGROUP="${DATA_ANALYSIS_ATHENA_WG:-co-intelligence-data-analysis}" \
    --from-literal=CORS_ALLOW_ORIGINS="${CORS_ALLOW_ORIGINS:-}" \
    --from-literal=AUTO_GENERATE_SCHEMAS="${AUTO_GENERATE_SCHEMAS:-true}" \
    --from-literal=TINKER_BASE_PATH="${TINKER_BASE_PATH:-/app}" \
    | kubectl apply -f -
echo "✓ Secrets created"

# Apply IRSA service account and observability DaemonSet
echo "Applying IRSA service account and X-Ray daemonset..."
kubectl apply -f k8s/sa-backend-irsa.yaml
kubectl apply -f k8s/xray-daemonset.yaml
echo "Applying observability stack..."
kubectl apply -f k8s/observability/
echo "✓ Observability stack applied"

echo "Waiting for observability LoadBalancers..."
OBS_ATTEMPTS=30
for i in $(seq 1 $OBS_ATTEMPTS); do
    GRAFANA_LB=$(kubectl get svc grafana -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
    PROMETHEUS_LB=$(kubectl get svc prometheus -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
    JAEGER_LB=$(kubectl get svc jaeger -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
    if [ -n "$GRAFANA_LB" ] && [ -n "$PROMETHEUS_LB" ] && [ -n "$JAEGER_LB" ]; then break; fi
    sleep 10
done
if [ -n "$GRAFANA_LB" ]; then
    NEXT_PUBLIC_GRAFANA_URL="http://$GRAFANA_LB"
    echo "Configuring Grafana root URL..."
    kubectl set env deployment/grafana GF_SERVER_DOMAIN="$GRAFANA_LB" \
        GF_SERVER_ROOT_URL="http://$GRAFANA_LB"
    kubectl rollout restart deployment/grafana
fi
if [ -n "$PROMETHEUS_LB" ]; then
    NEXT_PUBLIC_PROMETHEUS_URL="http://$PROMETHEUS_LB"
fi
if [ -n "$JAEGER_LB" ]; then
    NEXT_PUBLIC_JAEGER_URL="http://$JAEGER_LB"
fi
echo "Observability endpoints:"
echo "  Grafana: ${NEXT_PUBLIC_GRAFANA_URL:-pending}"
echo "  Prometheus: ${NEXT_PUBLIC_PROMETHEUS_URL:-pending}"
echo "  Jaeger: ${NEXT_PUBLIC_JAEGER_URL:-pending}"

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

echo "Deploying fine-tuning worker..."
sed -e "s|<ACCOUNT_ID>|$ACCOUNT_ID|g" -e "s|<IMAGE_TAG>|$IMAGE_TAG|g" k8s/fine-tuning-worker-deployment.yaml | kubectl apply -f -
echo "✓ Fine-tuning worker applied"

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
docker build \
  --build-arg NEXT_PUBLIC_API_URL="" \
  --build-arg NEXT_PUBLIC_GRAFANA_URL="${NEXT_PUBLIC_GRAFANA_URL:-}" \
  --build-arg NEXT_PUBLIC_PROMETHEUS_URL="${NEXT_PUBLIC_PROMETHEUS_URL:-}" \
  --build-arg NEXT_PUBLIC_JAEGER_URL="${NEXT_PUBLIC_JAEGER_URL:-}" \
  -t $ECR_FRONTEND:$IMAGE_TAG ./frontend
docker push $ECR_FRONTEND:$IMAGE_TAG
echo "✓ Images pushed with tag $IMAGE_TAG"

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
            --from-literal=REDIS_URL="rediss://$REDIS_ENDPOINT:6379/0" \
            --from-literal=GEMINI_API_KEY="${GEMINI_API_KEY:-}" \
            --from-literal=GROQ_API_KEY="${GROQ_API_KEY:-}" \
            --from-literal=TAVILY_API_KEY="${TAVILY_API_KEY:-}" \
            --from-literal=TINKER_API_KEY="${TINKER_API_KEY:-}" \
            --from-literal=GMAIL_SMTP_USER="${GMAIL_SMTP_USER:-}" \
            --from-literal=GMAIL_SMTP_APP_PASSWORD="${GMAIL_SMTP_APP_PASSWORD:-}" \
            --from-literal=GMAIL_SMTP_FROM_NAME="${GMAIL_SMTP_FROM_NAME:-Co-Intelligence}" \
            --from-literal=AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-}" \
            --from-literal=AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-}" \
            --from-literal=AWS_REGION="$AWS_REGION" \
            --from-literal=DATA_ANALYSIS_STATE_MACHINE_ARN="$DATA_ANALYSIS_SFN_ARN" \
            --from-literal=DATA_ANALYSIS_GLUE_DATABASE="${DATA_ANALYSIS_GLUE_DB:-co_intelligence_data_analysis}" \
            --from-literal=DATA_ANALYSIS_ATHENA_WORKGROUP="${DATA_ANALYSIS_ATHENA_WG:-co-intelligence-data-analysis}" \
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
if [ -n "$BACKEND_LB" ]; then
    echo "Backend: http://$BACKEND_LB"
fi
if [ -n "$NEXT_PUBLIC_GRAFANA_URL" ] || [ -n "$NEXT_PUBLIC_PROMETHEUS_URL" ] || [ -n "$NEXT_PUBLIC_JAEGER_URL" ]; then
    echo ""
    echo "Observability:"
    echo "  Grafana: ${NEXT_PUBLIC_GRAFANA_URL:-pending}"
    echo "  Prometheus: ${NEXT_PUBLIC_PROMETHEUS_URL:-pending}"
    echo "  Jaeger: ${NEXT_PUBLIC_JAEGER_URL:-pending}"
fi
echo ""
echo "Commands:"
echo "  kubectl get pods"
echo "  kubectl logs -f deployment/backend"
echo ""
echo "Starting observability port-forwards (Grafana/Prometheus/Jaeger)..."
kubectl port-forward svc/grafana 3000:3000 >/tmp/grafana-port-forward.log 2>&1 &
kubectl port-forward svc/prometheus 9090:9090 >/tmp/prometheus-port-forward.log 2>&1 &
kubectl port-forward svc/jaeger 16686:16686 >/tmp/jaeger-port-forward.log 2>&1 &
echo "✓ Port-forwards running (logs in /tmp/*-port-forward.log)"
