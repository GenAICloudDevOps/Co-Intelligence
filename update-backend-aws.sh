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
    --query 'Stacks[0].Outputs[?OutputKey==`BackendECRUri`].OutputValue' \
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

echo "🔐 Syncing Tinker env to app-secrets (if present in .env)..."
if [ -f "../.env" ]; then
  TINKER_API_KEY=$(python3 - <<'PY'
import os
from pathlib import Path

env_path = Path("../.env")
val = ""
for line in env_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    if k.strip() == "TINKER_API_KEY":
        val = v.strip().strip('"').strip("'")
        break
print(val)
PY
)
  TINKER_BASE_PATH=$(python3 - <<'PY'
from pathlib import Path

env_path = Path("../.env")
val = ""
for line in env_path.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    if k.strip() == "TINKER_BASE_PATH":
        val = v.strip().strip('"').strip("'")
        break
print(val)
PY
)
  if [ -n "${TINKER_API_KEY:-}" ] || [ -n "${TINKER_BASE_PATH:-}" ]; then
    patch='{"stringData":{'
    first=1
    if [ -n "${TINKER_API_KEY:-}" ]; then
      patch="$patch\"TINKER_API_KEY\":\"$TINKER_API_KEY\""
      first=0
    fi
    if [ -n "${TINKER_BASE_PATH:-}" ]; then
      if [ "$first" -eq 0 ]; then patch="$patch,"; fi
      patch="$patch\"TINKER_BASE_PATH\":\"$TINKER_BASE_PATH\""
    fi
    patch="$patch}}"
    kubectl patch secret app-secrets --type merge -p "$patch" >/dev/null
    echo "✓ app-secrets updated"
  else
    echo "ℹ️  No Tinker values found in .env; skipping secret patch"
  fi
else
  echo "ℹ️  No .env found; skipping secret patch"
fi

echo "🚀 Restarting backend deployment..."
kubectl rollout restart deployment/backend
kubectl rollout status deployment/backend

echo "✅ Backend updated successfully!"
