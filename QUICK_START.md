# Co-Intelligence - Quick Start Guide

## Prerequisites (Do Once)

### 1. Copy and configure .env file
```bash
cp .env.template .env
# Edit .env with your AWS credentials and API keys
```

### 2. Deploy CloudFormation Stack
```bash
cd infrastructure
aws cloudformation create-stack \
  --stack-name co-intelligence \
  --template-body file://infra_without_eks.yaml \
  --parameters ParameterKey=DBUsername,ParameterValue=cointelligence \
               ParameterKey=DBPassword,ParameterValue=SecurePass123! \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region us-east-1

# Wait for completion (10 minutes)
aws cloudformation wait stack-create-complete --stack-name co-intelligence --region us-east-1
```

### 3. Create EKS Cluster (AWS Console)
1. Go to **AWS Console → EKS → Create cluster**
2. Name: `co-intelligence-cluster`
3. Use default VPC (172.31.0.0/16)
4. Select 2+ subnets in different AZs
5. Create cluster (10 minutes)

### 4. Create Node Group (AWS Console)
1. Go to **Cluster → Compute → Add node group**
2. Name: `co-intelligence-nodes`
3. Instance type: `t3.medium`
4. Min: 1, Max: 3, Desired: 1
5. Create (5 minutes)

---

## Deploy Application (One Command!)

```bash
./deploy.sh
```

**That's it!** The script will:
- Configure RDS
- Build Docker images
- Push to ECR
- Deploy to Kubernetes
- Display URLs

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

### Clean Up (delete K8s resources only)
```bash
./cleanup.sh
```

### Redeploy Everything
```bash
./cleanup.sh
./deploy.sh
```

---

## Troubleshooting

### Script fails with "command not found"
```bash
chmod +x *.sh
```

### AWS credentials error
Check `.env` file has correct AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY

### kubectl connection error
```bash
aws eks update-kubeconfig --name co-intelligence-cluster --region us-east-1
```

### Backend not healthy
```bash
./logs.sh backend
# Check for database connection errors
```

### Frontend 404 errors
```bash
./update-frontend.sh
# Rebuilds with correct backend URL
```

---

## Complete Cleanup (Delete Everything)

```bash
# 1. Delete Kubernetes resources
./cleanup.sh

# 2. Delete EKS node group (AWS Console)
# 3. Delete EKS cluster (AWS Console)

# 4. Delete CloudFormation stack
aws cloudformation delete-stack --stack-name co-intelligence --region us-east-1
```

---

## File Structure

```
Co-Intelligence/
├── deploy.sh              # Main deployment script
├── update-backend.sh      # Update backend only
├── update-frontend.sh     # Update frontend only
├── logs.sh               # View logs
├── status.sh             # Check deployment status
├── cleanup.sh            # Delete K8s resources
├── .env                  # Your configuration (create from .env.template)
├── .env.template         # Template for .env
├── backend/              # Backend code
├── frontend/             # Frontend code
├── k8s/                  # Kubernetes manifests
└── infrastructure/       # CloudFormation templates
```

---

## Cost Estimate

- **EKS Cluster**: ~$73/month
- **RDS db.t3.medium**: ~$30/month
- **EC2 t3.medium nodes**: ~$30/month
- **LoadBalancers**: ~$20/month
- **Total**: ~$150/month

---

## Manual Deployment Steps (Alternative to deploy.sh)

If you prefer to deploy manually instead of using `./deploy.sh`:

### 1. Verify Environment
Ensure `.env` file exists with all required variables

### 2. Get CloudFormation Outputs
```bash
aws cloudformation describe-stacks --stack-name co-intelligence --region us-east-1 --query 'Stacks[0].Outputs'
aws sts get-caller-identity --query Account --output text
```
Note: RDSEndpoint, BackendECRUri, FrontendECRUri, Account ID

### 3. Verify RDS
```bash
# Get DB instance ID
aws rds describe-db-instances --region us-east-1

# Wait for RDS to be available
aws rds wait db-instance-available --db-instance-identifier <DB_ID> --region us-east-1
```

### 4. Configure kubectl
```bash
aws eks update-kubeconfig --name co-intelligence-cluster --region us-east-1
kubectl get nodes
```

### 5. Login to ECR
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
```

### 6. Build and Push Backend
```bash
cd backend
docker build -t co-intelligence-backend .
docker tag co-intelligence-backend:latest <BACKEND_ECR_URI>:latest
docker push <BACKEND_ECR_URI>:latest
cd ..
```

### 7. Create Kubernetes Secrets
```bash
kubectl create secret generic app-secrets \
  --from-literal=DATABASE_URL="postgres://<USER>:<PASS>@<RDS_ENDPOINT>:5432/postgres?ssl=require" \
  --from-literal=SECRET_KEY="<YOUR_SECRET_KEY>" \
  --from-literal=GEMINI_API_KEY="<YOUR_KEY>" \
  --from-literal=GROQ_API_KEY="<YOUR_KEY>" \
  --from-literal=AWS_ACCESS_KEY_ID="<YOUR_KEY>" \
  --from-literal=AWS_SECRET_ACCESS_KEY="<YOUR_KEY>" \
  --from-literal=AWS_REGION="us-east-1" \
  --dry-run=client -o yaml | kubectl apply -f -
```

### 8. Deploy Backend
```bash
# Update k8s/backend-deployment.yaml - replace <ACCOUNT_ID> with your account ID
sed "s|<ACCOUNT_ID>|<YOUR_ACCOUNT_ID>|g" k8s/backend-deployment.yaml | kubectl apply -f -
kubectl apply -f k8s/backend-service.yaml
kubectl patch svc backend -p '{"spec":{"type":"LoadBalancer"}}'

# Wait for LoadBalancer URL
kubectl get svc backend -w
```

### 9. Wait for Backend Health
```bash
# Get backend URL
BACKEND_URL=$(kubectl get svc backend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Test health endpoint
curl http://$BACKEND_URL:8000/health
```

### 10. Build and Push Frontend
```bash
cd frontend
docker build --build-arg NEXT_PUBLIC_API_URL=http://<BACKEND_URL>:8000 -t co-intelligence-frontend .
docker tag co-intelligence-frontend:latest <FRONTEND_ECR_URI>:latest
docker push <FRONTEND_ECR_URI>:latest
cd ..
```

### 11. Deploy Frontend
```bash
# Update k8s/frontend-deployment.yaml - replace <ACCOUNT_ID>
sed "s|<ACCOUNT_ID>|<YOUR_ACCOUNT_ID>|g" k8s/frontend-deployment.yaml | kubectl apply -f -
kubectl apply -f k8s/frontend-service.yaml

# Wait for LoadBalancer URL
kubectl get svc frontend -w
```

### 12. Verify Deployment
```bash
kubectl get pods
kubectl get svc
```

**Time:** ~10-12 minutes

---

## Next Steps After Deployment

1. Open the Frontend URL in your browser
2. Click **Register** to create an account
3. Enter email, username, and password
4. You'll be auto-logged in
5. Click **Launch** on AI Chat
6. Start chatting with AI!

---

## Support

For issues or questions, check:
- `./logs.sh backend` for backend errors
- `./logs.sh frontend` for frontend errors
- `./status.sh` for deployment status
- DEPLOYMENT_GUIDE.md for detailed manual steps
