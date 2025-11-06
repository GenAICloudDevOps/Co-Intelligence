#!/bin/bash

SERVICE=${1:-backend}

if [ "$SERVICE" != "backend" ] && [ "$SERVICE" != "frontend" ]; then
    echo "Usage: ./logs.sh [backend|frontend]"
    exit 1
fi

echo "📋 Viewing $SERVICE logs (Ctrl+C to exit)..."
kubectl logs -f deployment/$SERVICE
