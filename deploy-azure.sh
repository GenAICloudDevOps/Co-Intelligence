#!/bin/bash
set -e

echo "=========================================="
echo "Co-Intelligence Azure Deployment"
echo "=========================================="

command -v az >/dev/null 2>&1 || { echo "Azure CLI required"; exit 1; }
command -v terraform >/dev/null 2>&1 || { echo "terraform required"; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "kubectl required"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "docker required"; exit 1; }

TERRAFORM_DIR="infrastructure/azure"

# Auto-detect resource group and location from Azure
echo "Auto-detecting Azure resource group..."
RG_INFO=$(az group list --query "[0].{name:name, location:location}" -o tsv 2>/dev/null)
if [ -z "$RG_INFO" ]; then
    echo "Error: No resource group found. Make sure you're logged in: az login"
    exit 1
fi
DETECTED_RG=$(echo "$RG_INFO" | cut -f1)
DETECTED_LOCATION=$(echo "$RG_INFO" | cut -f2)
echo "✓ Found resource group: $DETECTED_RG ($DETECTED_LOCATION)"

# Update terraform variables with detected values
cat > "$TERRAFORM_DIR/terraform.tfvars" << EOF
resource_group_name = "$DETECTED_RG"
location            = "$DETECTED_LOCATION"
EOF
echo "✓ Updated terraform.tfvars"

# Initialize and apply Terraform if no state exists
if [ ! -f "$TERRAFORM_DIR/terraform.tfstate" ]; then
    echo "Running Terraform..."
    cd $TERRAFORM_DIR
    terraform init
    terraform apply -auto-approve
    cd ../..
fi

# Deploy Azure Function
echo "Deploying Azure Function..."
FUNC_APP_NAME=$(cd $TERRAFORM_DIR && terraform output -raw code_executor_url | sed 's|https://||' | sed 's|\..*||')
cd $TERRAFORM_DIR/function
zip -r ../function.zip .
az functionapp deployment source config-zip \
  -g $(cd .. && terraform output -raw resource_group) \
  -n $FUNC_APP_NAME \
  --src ../function.zip
rm ../function.zip
cd ../../..
echo "✓ Azure Function deployed"

# Load API keys from .env
if [ -f ".env" ]; then
    echo "Loading API keys from .env..."
    export $(grep -E '^(GEMINI_API_KEY|GROQ_API_KEY|TAVILY_API_KEY|TINKER_API_KEY|TINKER_BASE_PATH|AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|AWS_REGION)=' .env | xargs)
fi

echo "Fetching Terraform outputs..."
cd $TERRAFORM_DIR

RESOURCE_GROUP=$(terraform output -raw resource_group)
AKS_CLUSTER=$(terraform output -raw aks_cluster_name)
DB_HOST=$(terraform output -raw db_host)
DB_NAME=$(terraform output -raw db_name)
DB_USERNAME=$(terraform output -raw db_username)
DB_PASSWORD=$(terraform output -raw db_password)
SECRET_KEY=$(terraform output -raw secret_key)
ACR_SERVER=$(terraform output -raw acr_login_server)
ACR_USERNAME=$(terraform output -raw acr_admin_username)
ACR_PASSWORD=$(terraform output -raw acr_admin_password)
STORAGE_ACCOUNT=$(terraform output -raw storage_account)
CODE_EXECUTOR_URL=$(terraform output -raw code_executor_url)

cd ../..

echo "✓ Terraform outputs retrieved"

# Update .env with infrastructure values
echo "Updating .env..."
cat > .env << EOF
# AI API Keys
GEMINI_API_KEY=${GEMINI_API_KEY:-}
GROQ_API_KEY=${GROQ_API_KEY:-}
TAVILY_API_KEY=${TAVILY_API_KEY:-}
TINKER_API_KEY=${TINKER_API_KEY:-}
TINKER_BASE_PATH=${TINKER_BASE_PATH:-/app}

# AWS Credentials (for Bedrock)
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID:-}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-}
AWS_REGION=${AWS_REGION:-us-east-1}

# Infrastructure (auto-populated)
DATABASE_URL=postgres://$DB_USERNAME:$DB_PASSWORD@$DB_HOST:5432/$DB_NAME?sslmode=require
SECRET_KEY=$SECRET_KEY
AZURE_STORAGE_ACCOUNT=$STORAGE_ACCOUNT
EOF
echo "✓ .env updated"

# Login to ACR
echo "Logging into Azure Container Registry..."
docker login $ACR_SERVER -u $ACR_USERNAME -p $ACR_PASSWORD
echo "✓ ACR login successful"

# Build and push images
echo "Building and pushing backend..."
docker build -t $ACR_SERVER/backend:latest ./backend
docker push $ACR_SERVER/backend:latest

echo "Building and pushing frontend..."
docker build --build-arg NEXT_PUBLIC_API_URL="" -t $ACR_SERVER/frontend:latest ./frontend
docker push $ACR_SERVER/frontend:latest
echo "✓ Images pushed"

# Configure kubectl
echo "Configuring kubectl for AKS..."
az aks get-credentials --resource-group $RESOURCE_GROUP --name $AKS_CLUSTER --overwrite-existing
echo "✓ kubectl configured"

# Create namespace
kubectl create namespace co-intelligence --dry-run=client -o yaml | kubectl apply -f -

# Create ACR pull secret (sandbox can't use managed identity)
echo "Creating ACR pull secret..."
kubectl create secret docker-registry acr-secret \
    --docker-server=$ACR_SERVER \
    --docker-username=$ACR_USERNAME \
    --docker-password=$ACR_PASSWORD \
    -n co-intelligence --dry-run=client -o yaml | kubectl apply -f -
echo "✓ ACR secret created"

# Create secrets
echo "Creating Kubernetes secrets..."
kubectl delete secret app-secrets -n co-intelligence 2>/dev/null || true
kubectl create secret generic app-secrets \
    --namespace co-intelligence \
    --from-literal=DATABASE_URL="postgres://$DB_USERNAME:$DB_PASSWORD@$DB_HOST:5432/$DB_NAME?sslmode=require" \
    --from-literal=SECRET_KEY="$SECRET_KEY" \
    --from-literal=AZURE_STORAGE_ACCOUNT="$STORAGE_ACCOUNT" \
    --from-literal=CODE_EXECUTOR_URL="$CODE_EXECUTOR_URL" \
    --from-literal=GEMINI_API_KEY="${GEMINI_API_KEY:-}" \
    --from-literal=GROQ_API_KEY="${GROQ_API_KEY:-}" \
    --from-literal=TAVILY_API_KEY="${TAVILY_API_KEY:-}" \
    --from-literal=TINKER_API_KEY="${TINKER_API_KEY:-}" \
    --from-literal=TINKER_BASE_PATH="${TINKER_BASE_PATH:-/app}" \
    --from-literal=AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-}" \
    --from-literal=AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-}" \
    --from-literal=AWS_REGION="${AWS_REGION:-us-east-1}"
echo "✓ Secrets created"

# Generate K8s manifests
echo "Generating Kubernetes manifests..."
mkdir -p k8s-azure

cat > k8s-azure/backend.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: co-intelligence
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
      - name: backend
        image: $ACR_SERVER/backend:latest
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: app-secrets
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: co-intelligence
spec:
  selector:
    app: backend
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
EOF

cat > k8s-azure/frontend.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: co-intelligence
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: frontend
        image: $ACR_SERVER/frontend:latest
        ports:
        - containerPort: 3000
        env:
        - name: NEXT_PUBLIC_API_URL
          value: ""
        - name: BACKEND_URL
          value: "http://backend:8000"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: co-intelligence
spec:
  selector:
    app: frontend
  ports:
  - port: 80
    targetPort: 3000
  type: LoadBalancer
EOF

cat > k8s-azure/hpa.yaml << EOF
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: co-intelligence
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 2
  maxReplicas: 3
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: frontend-hpa
  namespace: co-intelligence
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: frontend
  minReplicas: 2
  maxReplicas: 3
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
EOF

echo "✓ Manifests generated"

# Apply manifests with image substitution
echo "Deploying to AKS..."
for f in k8s-azure/*.yaml; do
    sed "s|ACR_SERVER_PLACEHOLDER|$ACR_SERVER|g" "$f" | kubectl apply -f -
done
echo "✓ Deployed"

# Wait for LoadBalancer
echo "Waiting for LoadBalancer IP..."
for i in {1..30}; do
    EXTERNAL_IP=$(kubectl get svc frontend -n co-intelligence -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
    if [ -n "$EXTERNAL_IP" ]; then break; fi
    sleep 10
done

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo "Frontend: http://$EXTERNAL_IP"
echo ""
echo "Commands:"
echo "  kubectl get pods -n co-intelligence"
echo "  kubectl logs -f deployment/backend -n co-intelligence"
