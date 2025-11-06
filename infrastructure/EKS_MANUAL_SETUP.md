# Manual EKS Setup Instructions

## Step 1: Deploy CloudFormation Stack

```bash
cd infrastructure

aws cloudformation create-stack \
  --stack-name co-intelligence \
  --template-body file://infra_without_eks.yaml \
  --parameters ParameterKey=DBUsername,ParameterValue=cointelligence \
               ParameterKey=DBPassword,ParameterValue=SecurePass123! \
  --capabilities CAPABILITY_IAM \
  --region us-east-1

# Wait for completion (5-10 minutes)
aws cloudformation wait stack-create-complete \
  --stack-name co-intelligence \
  --region us-east-1

# Get outputs (SAVE THESE!)
aws cloudformation describe-stacks \
  --stack-name co-intelligence \
  --region us-east-1 \
  --query 'Stacks[0].Outputs'
```

## Step 2: Create EKS Cluster (AWS Console)

1. Go to **EKS Console**: https://console.aws.amazon.com/eks/home?region=us-east-1

2. Click **Add cluster** → **Create**

3. **Configure cluster:**
   - Name: `co-intelligence-cluster`
   - Kubernetes version: `1.28`
   - Cluster service role: Select `co-intelligence-eks-cluster-role` (from CloudFormation outputs)

4. Click **Next**

5. **Specify networking:**
   - VPC: Select the VPC ID from CloudFormation outputs
   - Subnets: Select BOTH subnet IDs from outputs
   - Security groups: Select the EKS security group from outputs
   - Cluster endpoint access: **Public**

6. Click **Next** → **Next** → **Create**

7. Wait 10-15 minutes for cluster creation

## Step 3: Create Node Group (AWS Console)

1. Once cluster is **Active**, go to cluster → **Compute** tab

2. Click **Add node group**

3. **Configure node group:**
   - Name: `co-intelligence-nodes`
   - Node IAM role: Select `co-intelligence-eks-node-role` (from CloudFormation outputs)

4. Click **Next**

5. **Set compute and scaling configuration:**
   - AMI type: `Amazon Linux 2 (AL2_x86_64)`
   - Instance type: `t3.medium`
   - Disk size: `20 GB`
   - Desired size: `1`
   - Minimum size: `1`
   - Maximum size: `3`

6. Click **Next**

7. **Specify networking:**
   - Subnets: Select BOTH subnets
   - Allow remote access: **Disabled** (or configure SSH if needed)

8. Click **Next** → **Create**

9. Wait 5-10 minutes for node group creation

## Step 4: Configure kubectl

```bash
# Update kubeconfig
aws eks update-kubeconfig \
  --name co-intelligence-cluster \
  --region us-east-1

# Verify connection
kubectl get nodes
```

You should see 1 node in Ready state.

## Step 5: Continue with Docker Build & Deploy

Now proceed with the main README instructions starting from "Build and Push Docker Images".

## Summary of What Was Created

**CloudFormation:**
- VPC with 2 subnets (us-east-1a, us-east-1b)
- RDS PostgreSQL
- ECR repositories (backend, frontend)
- S3 bucket
- IAM roles for EKS
- Security groups

**Manual (Console):**
- EKS Cluster
- EKS Node Group (1-3 t3.medium nodes)
