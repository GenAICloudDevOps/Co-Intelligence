# Co-Intelligence AWS Deployment Guide

Deploy Co-Intelligence to AWS using EKS, RDS PostgreSQL, and ECR.

## Prerequisites

- [AWS CLI](https://aws.amazon.com/cli/) installed and configured
- Docker installed
- kubectl installed
- jq installed

## Fresh Deployment

### Step 1: Configure AWS CLI

```bash
# Configure credentials
aws configure

# Verify
aws sts get-caller-identity
```

### Step 2: Prepare Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API keys:
# - GEMINI_API_KEY (from Google AI Studio)
# - GROQ_API_KEY
# - TAVILY_API_KEY
# - AWS_ACCESS_KEY_ID
# - AWS_SECRET_ACCESS_KEY
```

### Step 3: Create Infrastructure

```bash
# Deploy CloudFormation stack
aws cloudformation create-stack \
  --stack-name co-intelligence \
  --template-body file://infrastructure/infra.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1

# Wait for completion (~15-20 min)
aws cloudformation wait stack-create-complete \
  --stack-name co-intelligence \
  --region us-east-1
```

This creates:
- ✅ VPC with subnets
- ✅ EKS Cluster (2-3 t3.medium nodes)
- ✅ RDS PostgreSQL 15
- ✅ ECR repositories (backend + frontend)
- ✅ S3 bucket
- ✅ Secrets Manager secrets
- ✅ Lambda for code execution

### Step 4: Deploy Application

```bash
# Make script executable
chmod +x deploy.sh

# Deploy
./deploy.sh
```

This will:
- ✅ Fetch CloudFormation outputs
- ✅ Update `.env` with infrastructure values
- ✅ Build and push Docker images to ECR
- ✅ Configure kubectl for EKS
- ✅ Create Kubernetes secrets
- ✅ Deploy backend and frontend pods
- ✅ Output the LoadBalancer URL

---

## Configuration

### CloudFormation Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `DBUsername` | `cointelligence` | Database username |

### Environment Variables

| Variable | Description |
|----------|-------------|
| `STACK_NAME` | CloudFormation stack name (default: co-intelligence) |
| `EKS_CLUSTER_NAME` | EKS cluster name (default: co-intelligence-cluster) |

---

## Resources Created

| Resource | Spec | Purpose |
|----------|------|---------|
| EKS Cluster | 2-3 t3.medium nodes | Kubernetes |
| RDS | PostgreSQL 15, db.t3.medium, 20GB | Database |
| ECR | 2 repos (backend, frontend) | Docker images |
| S3 | 1 bucket | File storage |
| Secrets Manager | 2 secrets | DB password, SECRET_KEY |
| Lambda | Python 3.11, 512MB | Code execution |
| VPC | 2 subnets | Networking |

---

## Monitoring

```bash
# Check pods
kubectl get pods

# View backend logs
kubectl logs -f deployment/backend

# View frontend logs
kubectl logs -f deployment/frontend

# Check HPA status
kubectl get hpa
```

---

## Update Deployment

After code changes:

```bash
./deploy.sh
```

Or update only images:

```bash
# Get ECR URI
ECR_BACKEND=$(aws cloudformation describe-stacks --stack-name co-intelligence \
  --query 'Stacks[0].Outputs[?OutputKey==`BackendECRUri`].OutputValue' --output text)

# Rebuild and push
docker build -t $ECR_BACKEND:latest ./backend
docker push $ECR_BACKEND:latest

# Restart pods
kubectl rollout restart deployment/backend
```

---

## Cleanup

```bash
# Delete K8s resources
kubectl delete -f k8s/

# Delete CloudFormation stack
aws cloudformation delete-stack --stack-name co-intelligence --region us-east-1
```

---

## Troubleshooting

### CloudFormation errors

```bash
# Check stack events
aws cloudformation describe-stack-events --stack-name co-intelligence --region us-east-1
```

### Pod not starting

```bash
kubectl describe pod <pod-name>
kubectl logs <pod-name>
```

### Database connection issues

RDS uses private VPC. Verify from within cluster:
```bash
kubectl exec -it deployment/backend -- nc -zv <RDS_ENDPOINT> 5432
```

---

## Cost Estimate

| Resource | Monthly Cost (approx) |
|----------|----------------------|
| EKS (2 t3.medium) | ~$70 |
| RDS (db.t3.medium) | ~$30 |
| ECR | ~$5 |
| S3 | ~$1 |
| Lambda | ~$1 |
| **Total** | **~$107/month** |

*Costs vary by usage. Use [AWS Pricing Calculator](https://calculator.aws) for accurate estimates.*
