#!/bin/bash
set -e

echo "🔄 Updating Backend..."

if [ -f ".env" ]; then
    # Load only needed vars to avoid shell-evaluating secrets with special chars
    export $(grep -E '^(AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|AWS_REGION|STACK_NAME)=' .env | xargs)
fi
export AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_REGION
STACK_NAME=${STACK_NAME:-co-intelligence}
AWS_REGION=${AWS_REGION:-us-east-1}

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_BACKEND=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`BackendECRRepository`].OutputValue' \
    --output text)

echo "🔐 Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

echo "🔨 Building backend image..."
cd backend
docker build -t co-intelligence-backend .
docker tag co-intelligence-backend:latest $ECR_BACKEND:latest

echo "📤 Pushing backend image..."
docker push $ECR_BACKEND:latest

echo "🚀 Restarting backend deployment..."
kubectl rollout restart deployment/backend
kubectl rollout status deployment/backend

echo "✅ Backend updated successfully!"
