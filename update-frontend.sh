#!/bin/bash
set -e

echo "🔄 Updating Frontend..."

if [ -f ".env" ]; then
    # Load only needed vars to avoid shell-evaluating secrets with special chars
    export $(grep -E '^(AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|AWS_REGION|STACK_NAME)=' .env | xargs)
fi
export AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_REGION
STACK_NAME=${STACK_NAME:-co-intelligence}
AWS_REGION=${AWS_REGION:-us-east-1}

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_FRONTEND=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`FrontendECRRepository`].OutputValue' \
    --output text)

BACKEND_URL=$(kubectl get svc backend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
if [ -z "$BACKEND_URL" ]; then
    echo "⚠️  Backend LoadBalancer hostname not found. Ensure backend service is running."
    exit 1
fi

echo "🔐 Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

echo "🔨 Building frontend image..."
cd frontend
docker build --build-arg NEXT_PUBLIC_API_URL=http://$BACKEND_URL:8000 -t co-intelligence-frontend .
docker tag co-intelligence-frontend:latest $ECR_FRONTEND:latest

echo "📤 Pushing frontend image..."
docker push $ECR_FRONTEND:latest

echo "🚀 Restarting frontend deployment..."
kubectl rollout restart deployment/frontend
kubectl rollout status deployment/frontend

echo "✅ Frontend updated successfully!"
