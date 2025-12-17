#!/bin/bash
set -e

echo "=========================================="
echo "Co-Intelligence GCP Deployment"
echo "=========================================="

command -v gcloud >/dev/null 2>&1 || { echo "gcloud CLI required"; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "kubectl required"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "docker required"; exit 1; }

# Load from .env if exists (local dev)
if [ -f ".env" ]; then
    echo "Loading from .env..."
    export $(grep -v '^#' .env | xargs)
fi

# Check if using CI variables or terraform
if [ -n "$BACKEND_REGISTRY" ] && [ -n "$DB_HOST" ]; then
    echo "Using environment variables..."
    PROJECT_ID=${GCP_PROJECT_ID}
    REGION=${GCP_REGION}
    GKE_CLUSTER=${GKE_CLUSTER_NAME}
    GKE_ZONE_VAL=${GKE_ZONE}
else
    echo "Fetching from Terraform outputs..."
    command -v terraform >/dev/null 2>&1 || { echo "terraform required"; exit 1; }
    TERRAFORM_DIR="infrastructure/gcp"
    cd $TERRAFORM_DIR
    PROJECT_ID=$(terraform output -raw project_id)
    REGION=$(terraform output -raw region)
    GKE_CLUSTER=$(terraform output -raw gke_cluster_name)
    GKE_ZONE_VAL=$(terraform output -raw gke_zone)
    DB_HOST=$(terraform output -raw db_host)
    DB_NAME=$(terraform output -raw db_name)
    DB_USERNAME=$(terraform output -raw db_username)
    DB_PASSWORD=$(terraform output -raw db_password)
    SECRET_KEY=$(terraform output -raw secret_key)
    BACKEND_REGISTRY=$(terraform output -raw backend_registry)
    FRONTEND_REGISTRY=$(terraform output -raw frontend_registry)
    BUCKET_NAME=$(terraform output -raw bucket_name)
    cd ../..
fi

echo "✓ Configuration loaded"

# Update .env with infrastructure values
echo "Updating .env..."
cat > .env << EOF
GEMINI_API_KEY=${GEMINI_API_KEY:-}
GROQ_API_KEY=${GROQ_API_KEY:-}
TAVILY_API_KEY=${TAVILY_API_KEY:-}
TINKER_API_KEY=${TINKER_API_KEY:-}
TINKER_BASE_PATH=${TINKER_BASE_PATH:-/app}
AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID:-}
AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-}
AWS_REGION=${AWS_REGION:-us-east-1}
DATABASE_URL=postgres://$DB_USERNAME:$DB_PASSWORD@$DB_HOST:5432/$DB_NAME
SECRET_KEY=$SECRET_KEY
GCS_BUCKET=$BUCKET_NAME
EOF
echo "✓ .env updated"

# Configure Docker for Artifact Registry
echo "Configuring Docker for Artifact Registry..."
gcloud auth configure-docker $REGION-docker.pkg.dev --quiet
echo "✓ Docker configured"

# Build and push images
echo "Building and pushing backend..."
docker build -t $BACKEND_REGISTRY/backend:latest ./backend
docker push $BACKEND_REGISTRY/backend:latest

echo "Building and pushing frontend..."
docker build --build-arg NEXT_PUBLIC_API_URL="" -t $FRONTEND_REGISTRY/frontend:latest ./frontend
docker push $FRONTEND_REGISTRY/frontend:latest
echo "✓ Images pushed"

# Configure kubectl
echo "Configuring kubectl for GKE..."
gcloud container clusters get-credentials $GKE_CLUSTER --zone $GKE_ZONE_VAL --project $PROJECT_ID
echo "✓ kubectl configured"

# Create namespace
kubectl create namespace co-intelligence --dry-run=client -o yaml | kubectl apply -f -

# Create secrets
echo "Creating Kubernetes secrets..."
kubectl delete secret app-secrets -n co-intelligence 2>/dev/null || true
kubectl create secret generic app-secrets \
    --namespace co-intelligence \
    --from-literal=DATABASE_URL="postgres://$DB_USERNAME:$DB_PASSWORD@$DB_HOST:5432/$DB_NAME" \
    --from-literal=SECRET_KEY="$SECRET_KEY" \
    --from-literal=GCS_BUCKET="$BUCKET_NAME" \
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
mkdir -p k8s-gcp

cat > k8s-gcp/backend.yaml << EOF
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
        image: $BACKEND_REGISTRY/backend:latest
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

cat > k8s-gcp/frontend.yaml << EOF
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
        image: $FRONTEND_REGISTRY/frontend:latest
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

cat > k8s-gcp/hpa.yaml << EOF
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

# Apply manifests
echo "Deploying to GKE..."
kubectl apply -f k8s-gcp/
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
