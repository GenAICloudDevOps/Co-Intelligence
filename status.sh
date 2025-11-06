#!/bin/bash

echo "📊 Co-Intelligence Deployment Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "🔹 Pods:"
kubectl get pods
echo ""

echo "🔹 Services:"
kubectl get svc
echo ""

echo "🔹 Deployments:"
kubectl get deployments
echo ""

BACKEND_URL=$(kubectl get svc backend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
FRONTEND_URL=$(kubectl get svc frontend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)

if [ ! -z "$BACKEND_URL" ]; then
    echo "🔹 Backend URL: http://$BACKEND_URL:8000"
    if curl -s http://$BACKEND_URL:8000/health > /dev/null 2>&1; then
        echo "   Status: ✅ Healthy"
    else
        echo "   Status: ❌ Not responding"
    fi
else
    echo "🔹 Backend URL: ⏳ Waiting for LoadBalancer..."
fi

if [ ! -z "$FRONTEND_URL" ]; then
    echo "🔹 Frontend URL: http://$FRONTEND_URL"
else
    echo "🔹 Frontend URL: ⏳ Waiting for LoadBalancer..."
fi
echo ""
