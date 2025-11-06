# Co-Intelligence V1.0 Beta - Complete Deployment Guide

## Prerequisites

1. **AWS Account** with credentials (Access Key ID & Secret Access Key)
2. **AWS CLI** installed and configured
3. **Docker** installed
4. **kubectl** installed
5. **Node.js 20+** and **Python 3.11+** (for local development)

## Step 1: Configure AWS Credentials

```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Default region: us-east-1
# Default output format: json
```

## Step 2: Deploy Infrastructure (Without EKS)

```bash
cd infrastructure

# Deploy CloudFormation stack
aws cloudformation create-stack \
  --stack-name co-intelligence \
  --template-body file://infra_without_eks.yaml \
  --parameters ParameterKey=DBUsername,ParameterValue=cointelligence \
               ParameterKey=DBPassword,ParameterValue=SecurePass123! \
  --capabilities CAPABILITY_IAM \
  --region us-east-1

# Wait for completion (takes ~10 minutes)
aws cloudformation wait stack-create-complete \
  --stack-name co-intelligence \
  --region us-east-1

# Get outputs
aws cloudformation describe-stacks \
  --stack-name co-intelligence \
  --region us-east-1 \
  --query 'Stacks[0].Outputs'
```

**Save these outputs:**
- VPC ID
- Subnet IDs
- RDS Endpoint
- ECR Repository URIs
- S3 Bucket Name

## Step 3: Create EKS Cluster (AWS Console)

**Why Console?** IAM permissions may restrict CLI/CloudFormation EKS creation.

1. Go to **AWS Console → EKS → Clusters → Create cluster**
2. **Cluster Configuration:**
   - Name: `co-intelligence-cluster`
   - Kubernetes version: 1.28 or later
   - Cluster service role: Use existing or create new
3. **Networking:**
   - VPC: Select default VPC (172.31.0.0/16)
   - Subnets: Select at least 2 subnets in different AZs
   - Security groups: Default
   - Cluster endpoint access: Public
4. **Create cluster** (takes ~10 minutes)

## Step 4: Create EKS Node Group

1. Go to **Cluster → Compute → Add node group**
2. **Node Group Configuration:**
   - Name: `co-intelligence-nodes`
   - Node IAM role: Create new or use existing with EKS policies
3. **Compute Configuration:**
   - AMI type: Amazon Linux 2
   - Instance type: `t3.medium`
   - Disk size: 20 GB
4. **Scaling Configuration:**
   - Minimum size: 1
   - Maximum size: 3
   - Desired size: 1
5. **Create** (takes ~5 minutes)

## Step 5: Configure RDS Access

### Make RDS Publicly Accessible
```bash
# Get RDS instance identifier
aws rds describe-db-instances --region us-east-1 --query 'DBInstances[0].DBInstanceIdentifier' --output text

# Modify RDS to be publicly accessible
aws rds modify-db-instance \
  --db-instance-identifier co-intelligence-db \
  --publicly-accessible \
  --apply-immediately \
  --region us-east-1
```

### Update Security Group
```bash
# Get RDS security group ID
SG_ID=$(aws rds describe-db-instances \
  --db-instance-identifier co-intelligence-db \
  --region us-east-1 \
  --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' \
  --output text)

# Allow access from anywhere (or restrict to EKS VPC)
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 5432 \
  --cidr 0.0.0.0/0 \
  --region us-east-1
```

### Disable SSL Requirement
```bash
# Create parameter group
aws rds create-db-parameter-group \
  --db-parameter-group-name co-intelligence-pg \
  --db-parameter-group-family postgres17 \
  --description "Co-Intelligence PostgreSQL parameters" \
  --region us-east-1

# Modify SSL setting
aws rds modify-db-parameter-group \
  --db-parameter-group-name co-intelligence-pg \
  --parameters "ParameterName=rds.force_ssl,ParameterValue=0,ApplyMethod=immediate" \
  --region us-east-1

# Apply parameter group to RDS
aws rds modify-db-instance \
  --db-instance-identifier co-intelligence-db \
  --db-parameter-group-name co-intelligence-pg \
  --apply-immediately \
  --region us-east-1

# Reboot RDS to apply changes
aws rds reboot-db-instance \
  --db-instance-identifier co-intelligence-db \
  --region us-east-1
```

## Step 6: Build and Push Docker Images

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

# Build and push frontend (will be updated later with backend URL)
cd ../frontend
docker build --build-arg NEXT_PUBLIC_API_URL=http://localhost:8000 -t co-intelligence-frontend .
docker tag co-intelligence-frontend:latest $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/co-intelligence-frontend:latest
docker push $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/co-intelligence-frontend:latest
```

## Step 7: Configure kubectl for EKS

```bash
aws eks update-kubeconfig --name co-intelligence-cluster --region us-east-1

# Verify connection
kubectl get nodes
```

## Step 8: Create Kubernetes Secrets

```bash
cd k8s

# Get RDS endpoint
RDS_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier co-intelligence-db \
  --region us-east-1 \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text)

# Create secrets file
cat > secrets.yaml << EOF
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
stringData:
  DATABASE_URL: "postgres://cointelligence:SecurePass123%21@${RDS_ENDPOINT}:5432/postgres"
  SECRET_KEY: "your-secret-key-change-in-production-min-32-chars"
  GEMINI_API_KEY: "your-gemini-api-key"
  GROQ_API_KEY: "your-groq-api-key"
  AWS_ACCESS_KEY_ID: "your-aws-access-key"
  AWS_SECRET_ACCESS_KEY: "your-aws-secret-key"
  AWS_REGION: "us-east-1"
EOF

# Apply secrets
kubectl apply -f secrets.yaml
```

## Step 9: Deploy Backend to EKS

```bash
# Update backend deployment with your account ID
sed -i "s/<ACCOUNT_ID>/$ACCOUNT_ID/g" backend-deployment.yaml

# Deploy backend
kubectl apply -f backend-deployment.yaml

# Expose backend as LoadBalancer
kubectl apply -f backend-service.yaml
kubectl patch svc backend -p '{"spec":{"type":"LoadBalancer"}}'

# Wait for LoadBalancer (takes ~2 minutes)
kubectl get svc backend -w

# Get backend URL
BACKEND_URL=$(kubectl get svc backend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "Backend URL: http://$BACKEND_URL:8000"
```

## Step 10: Rebuild and Deploy Frontend with Backend URL

```bash
cd ../frontend

# Rebuild frontend with backend LoadBalancer URL
docker build --build-arg NEXT_PUBLIC_API_URL=http://$BACKEND_URL:8000 -t co-intelligence-frontend .
docker tag co-intelligence-frontend:latest $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/co-intelligence-frontend:latest
docker push $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/co-intelligence-frontend:latest

# Deploy frontend
cd ../k8s
sed -i "s/<ACCOUNT_ID>/$ACCOUNT_ID/g" frontend-deployment.yaml
kubectl apply -f frontend-deployment.yaml
kubectl apply -f frontend-service.yaml

# Get frontend URL
kubectl get svc frontend -w
FRONTEND_URL=$(kubectl get svc frontend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "Frontend URL: http://$FRONTEND_URL"
```

## Step 11: Verify Deployment

```bash
# Check all pods are running
kubectl get pods

# Check services
kubectl get svc

# View backend logs
kubectl logs -f deployment/backend

# View frontend logs
kubectl logs -f deployment/frontend

# Test backend health
curl http://$BACKEND_URL:8000/health
```

## Step 12: Access Application

Open browser and navigate to: `http://$FRONTEND_URL`

1. Click **Register** to create an account
2. Enter email, username, and password
3. You'll be auto-logged in
4. Click **Launch** on AI Chat to start chatting

## Troubleshooting

### Backend Pod CrashLoopBackOff
```bash
kubectl logs deployment/backend
# Check DATABASE_URL, RDS connectivity, and secrets
```

### Frontend 404 Errors
```bash
# Rebuild frontend with correct backend URL
docker build --build-arg NEXT_PUBLIC_API_URL=http://$BACKEND_URL:8000 -t co-intelligence-frontend .
docker push $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/co-intelligence-frontend:latest
kubectl rollout restart deployment/frontend
```

### RDS Connection Issues
```bash
# Check security group allows port 5432
# Verify RDS is publicly accessible
# Test connection from pod
kubectl exec deployment/backend -- nc -zv $RDS_ENDPOINT 5432
```

### Authentication Errors
```bash
# Check bcrypt version in requirements.txt
# Should have: bcrypt==4.0.1
# Rebuild and redeploy backend
```

## Cleanup

```bash
# Delete Kubernetes resources
kubectl delete -f k8s/

# Delete EKS node group (AWS Console)
# Delete EKS cluster (AWS Console)

# Delete CloudFormation stack
aws cloudformation delete-stack --stack-name co-intelligence --region us-east-1

# Wait for deletion
aws cloudformation wait stack-delete-complete --stack-name co-intelligence --region us-east-1
```

## Important Notes

1. **RDS Password**: URL-encode special characters (e.g., `!` becomes `%21`)
2. **EKS VPC**: Use default VPC (172.31.0.0/16) for simplicity
3. **LoadBalancer**: Both frontend and backend need LoadBalancer type for browser access
4. **API Keys**: Get from:
   - Gemini: https://aistudio.google.com/app/apikey
   - Groq: https://console.groq.com/keys
   - AWS: Use your AWS credentials for Bedrock
5. **Costs**: EKS cluster (~$73/month), RDS (~$30/month), EC2 nodes (~$30/month)

## Environment Variables Reference

### Backend (.env)
```
DATABASE_URL=postgres://user:pass@host:5432/db
SECRET_KEY=min-32-chars-secret
GEMINI_API_KEY=your-key
GROQ_API_KEY=your-key
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-key
AWS_REGION=us-east-1
```

### Frontend (.env)
```
NEXT_PUBLIC_API_URL=http://backend-url:8000
```

## Architecture Summary

- **Frontend**: Next.js 14 on EKS (LoadBalancer)
- **Backend**: FastAPI on EKS (LoadBalancer)
- **Database**: AWS RDS PostgreSQL 17.4
- **Container Registry**: AWS ECR
- **Orchestration**: AWS EKS with t3.medium nodes
- **AI Models**: Gemini 2.5 Flash Lite, Groq Mixtral, AWS Bedrock Nova
- **Authentication**: JWT with bcrypt password hashing
