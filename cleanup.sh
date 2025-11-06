#!/bin/bash

echo "🗑️  Cleaning up Kubernetes resources..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "This will delete:"
echo "  - All pods"
echo "  - All services (LoadBalancers)"
echo "  - All deployments"
echo "  - All secrets"
echo ""
echo "This will NOT delete:"
echo "  - EKS cluster"
echo "  - CloudFormation stack (RDS, VPC, ECR)"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 1
fi

echo "🗑️  Deleting Kubernetes resources..."
kubectl delete -f k8s/ 2>/dev/null || true
kubectl delete secret app-secrets 2>/dev/null || true

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "To delete everything including EKS and CloudFormation:"
echo "  1. Delete EKS node group (AWS Console)"
echo "  2. Delete EKS cluster (AWS Console)"
echo "  3. Run: aws cloudformation delete-stack --stack-name co-intelligence --region us-east-1"
echo ""
