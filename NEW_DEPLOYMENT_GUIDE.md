# New Deployment Guide - From Scratch

## Prerequisites
- AWS CLI configured with credentials
- Docker installed
- kubectl installed
- Node.js 20+ (for local dev)
- Python 3.11+ (for local dev)

---

## Step 1: Configure Environment

```bash
cp .env.example .env
# Edit .env with your AWS credentials and API keys
```

**Required values:**
```bash
# Database (will be filled after CloudFormation)
DATABASE_URL=postgres://cointelligence:SecurePass123@<RDS_ENDPOINT>:5432/postgres

# AWS
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>

# API Keys
GEMINI_API_KEY=<your-key>
GROQ_API_KEY=<your-key>
TAVILY_API_KEY=<your-key>  # Optional

# Security
SECRET_KEY=<generate-random-string>
```

---

## Step 2: Deploy CloudFormation Stack (10-15 minutes)

```bash
cd infrastructure

aws cloudformation create-stack \
  --stack-name co-intelligence \
  --template-body file://infra_without_eks.yaml \
  --parameters \
    ParameterKey=DBUsername,ParameterValue=cointelligence \
    ParameterKey=DBPassword,ParameterValue=SecurePass123 \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region us-east-1

# Wait for completion
aws cloudformation wait stack-create-complete \
  --stack-name co-intelligence \
  --region us-east-1

# Get outputs
aws cloudformation describe-stacks \
  --stack-name co-intelligence \
  --region us-east-1 \
  --query 'Stacks[0].Outputs'
```

**What gets created:**
- ✅ VPC with public/private subnets
- ✅ RDS PostgreSQL (with SSL disabled via parameter group)
- ✅ ECR repositories (backend, frontend)
- ✅ S3 bucket
- ✅ Lambda function for code execution
- ✅ IAM roles and security groups
- ❌ **NOT created:** EKS cluster (manual step)

**Update .env with RDS endpoint from outputs**

---

## Step 3: Create EKS Cluster (10-15 minutes)

### Option A: AWS Console (Recommended)
1. Go to AWS Console → EKS → Create cluster
2. **Name:** `co-intelligence-cluster`
3. **Kubernetes version:** 1.28 or later
4. **VPC:** Select the VPC created by CloudFormation
5. **Subnets:** Select 2+ subnets in different AZs
6. **Security group:** Use the EKS security group from CloudFormation
7. Click **Create cluster** (10-15 minutes)

### Option B: AWS CLI
```bash
# Get values from CloudFormation outputs
EKS_ROLE_ARN=<from-outputs>
SUBNET_IDS=<from-outputs>

aws eks create-cluster \
  --name co-intelligence-cluster \
  --role-arn $EKS_ROLE_ARN \
  --resources-vpc-config subnetIds=$SUBNET_IDS \
  --region us-east-1

aws eks wait cluster-active \
  --name co-intelligence-cluster \
  --region us-east-1
```

---

## Step 4: Create Node Group (5-10 minutes)

### Option A: AWS Console (Recommended)
1. Go to Cluster → Compute → Add node group
2. **Name:** `co-intelligence-nodes`
3. **Node IAM role:** Select role from CloudFormation outputs
4. **Instance type:** `t3.medium`
5. **Scaling:** Min=1, Max=3, Desired=1
6. Click **Create** (5-10 minutes)

### Option B: AWS CLI
```bash
NODE_ROLE_ARN=<from-outputs>

aws eks create-nodegroup \
  --cluster-name co-intelligence-cluster \
  --nodegroup-name co-intelligence-nodes \
  --node-role $NODE_ROLE_ARN \
  --subnets $SUBNET_IDS \
  --instance-types t3.medium \
  --scaling-config minSize=1,maxSize=3,desiredSize=1 \
  --region us-east-1

aws eks wait nodegroup-active \
  --cluster-name co-intelligence-cluster \
  --nodegroup-name co-intelligence-nodes \
  --region us-east-1
```

---

## Step 5: Configure kubectl

```bash
aws eks update-kubeconfig \
  --name co-intelligence-cluster \
  --region us-east-1

# Verify connection
kubectl get nodes
```

**Expected output:**
```
NAME                         STATUS   ROLES    AGE   VERSION
ip-10-0-x-x.ec2.internal     Ready    <none>   1m    v1.28.x
```

---

## Step 6: Automated Deployment (12-15 minutes)

```bash
# Run automated deployment script
./deploy.sh
```

**What deploy.sh does:**
1. ✅ Verifies CloudFormation stack exists
2. ✅ Waits for RDS to be available
3. ✅ Gets AWS account ID automatically
4. ✅ Logs into ECR
5. ✅ Builds backend Docker image
6. ✅ Pushes backend to ECR
7. ✅ Builds frontend Docker image
8. ✅ Pushes frontend to ECR
9. ✅ Updates kubeconfig for EKS
10. ✅ Replaces `<ACCOUNT_ID>` in deployment YAMLs
11. ✅ Creates Kubernetes secrets from .env
12. ✅ Deploys backend to EKS
13. ✅ Deploys frontend to EKS
14. ✅ Waits for LoadBalancers
15. ✅ Displays access URLs

---

## Step 7: Access Application

After deployment completes:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎉 Deployment Complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Frontend: http://<frontend-lb>.us-east-1.elb.amazonaws.com
Backend:  http://<backend-lb>.us-east-1.elb.amazonaws.com:8000
```

**Test it:**
```bash
# Check backend health
curl http://<backend-lb>:8000/health

# Open frontend in browser
open http://<frontend-lb>
```

---

## Step 8: Seed Barista Menu (Optional)

```bash
BACKEND_POD=$(kubectl get pods -l app=backend -o jsonpath='{.items[0].metadata.name}')
kubectl exec -it $BACKEND_POD -- python -m apps.agentic_barista.seed_menu
```

---

## Architecture Flow

```
User → Frontend (EKS) → Backend (EKS) → RDS PostgreSQL
                    ↓
                  Lambda (Code Execution)
                    ↓
                  S3 (File Storage)
```

---

## Key Features

### ✅ SSL Handled Automatically
- CloudFormation creates RDS with `rds.force_ssl=0`
- No SSL workarounds needed in code
- Clean, simple DATABASE_URL

### ✅ Account ID Handled Automatically
- Deployment YAMLs use `<ACCOUNT_ID>` placeholder
- `deploy.sh` replaces with actual account ID
- No manual editing needed

### ✅ Secrets Managed Automatically
- `deploy.sh` creates Kubernetes secrets from `.env`
- All environment variables injected properly

---

## Verification Commands

```bash
# Check pods
kubectl get pods

# Expected output:
# NAME                        READY   STATUS    RESTARTS   AGE
# backend-xxxxxxxxxx-xxxxx    1/1     Running   0          2m
# frontend-xxxxxxxxxx-xxxxx   1/1     Running   0          2m

# Check services
kubectl get svc

# Check logs
kubectl logs -f deployment/backend
kubectl logs -f deployment/frontend

# Check HPA
kubectl get hpa
```

---

## Time Estimates

| Step | Time |
|------|------|
| CloudFormation | 10-15 min |
| EKS Cluster | 10-15 min |
| Node Group | 5-10 min |
| deploy.sh | 12-15 min |
| **Total** | **37-55 min** |

---

## Troubleshooting

### Backend CrashLoopBackOff
```bash
kubectl logs deployment/backend

# Common issues:
# - Wrong DATABASE_URL in .env
# - Missing API keys
# - RDS not accessible
```

### Frontend ErrImagePull
```bash
kubectl describe pod <frontend-pod>

# Common issues:
# - Wrong account ID (should be auto-fixed by deploy.sh)
# - ECR login expired
```

### LoadBalancer Pending
```bash
kubectl describe svc frontend

# Usually takes 2-3 minutes to provision
```

---

## Cleanup

```bash
# Delete Kubernetes resources
kubectl delete -f k8s/

# Delete node group
aws eks delete-nodegroup \
  --cluster-name co-intelligence-cluster \
  --nodegroup-name co-intelligence-nodes \
  --region us-east-1

# Delete EKS cluster
aws eks delete-cluster \
  --name co-intelligence-cluster \
  --region us-east-1

# Delete CloudFormation stack (deletes RDS, ECR, Lambda, etc.)
aws cloudformation delete-stack \
  --stack-name co-intelligence \
  --region us-east-1

# Wait for deletion
aws cloudformation wait stack-delete-complete \
  --stack-name co-intelligence \
  --region us-east-1
```

---

## Cost Estimate (us-east-1)

| Resource | Monthly Cost |
|----------|--------------|
| EKS Cluster | ~$73 |
| EC2 (t3.medium x2) | ~$60 |
| RDS (db.t3.medium) | ~$50 |
| LoadBalancers (x2) | ~$32 |
| S3, Lambda, ECR | ~$5 |
| **Total** | **~$220/month** |

---

## Next Steps

1. **Register/Login** at frontend URL
2. **Try AI Chat** - Multi-model chat with document upload
3. **Try Agentic Barista** - LangGraph workflow demo
4. **Try Insurance Claims** - Role-based workflow app
5. **Monitor** - Check CloudWatch logs and metrics

---

## Support Documentation

- `docs/QUICK_START.md` - Detailed testing guide
- `DEPLOYMENT_FIX.md` - Common deployment issues
- `RDS_SSL_FIX.md` - SSL configuration details
- `AWS_ACCOUNT_ID.md` - Account ID setup
