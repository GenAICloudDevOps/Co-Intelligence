#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: aws_rds.sh [options]

Options:
  --stack NAME       CloudFormation stack name (default: co-intelligence)
  --region REGION    AWS region (default: us-east-1)
  --namespace NS     Kubernetes namespace (default: default)
  --db NAME          Database name (default: postgres)
  --image IMAGE      psql image (default: postgres:17)
  -h, --help         Show help

Environment variables (override defaults):
  STACK_NAME, AWS_REGION, NAMESPACE, DB_NAME, PSQL_IMAGE
EOF
}

STACK_NAME="${STACK_NAME:-co-intelligence}"
AWS_REGION="${AWS_REGION:-us-east-1}"
NAMESPACE="${NAMESPACE:-default}"
DB_NAME="${DB_NAME:-postgres}"
PSQL_IMAGE="${PSQL_IMAGE:-postgres:17}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --stack)
      STACK_NAME="$2"
      shift 2
      ;;
    --region)
      AWS_REGION="$2"
      shift 2
      ;;
    --namespace)
      NAMESPACE="$2"
      shift 2
      ;;
    --db)
      DB_NAME="$2"
      shift 2
      ;;
    --image)
      PSQL_IMAGE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

for cmd in aws kubectl jq; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing dependency: $cmd" >&2
    exit 1
  fi
done

RDS_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$AWS_REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`RDSEndpoint`].OutputValue' \
  --output text)

if [[ -z "${RDS_ENDPOINT:-}" || "${RDS_ENDPOINT}" == "None" ]]; then
  echo "Failed to resolve RDSEndpoint from stack '$STACK_NAME' in region '$AWS_REGION'." >&2
  exit 1
fi

SECRETS_JSON=$(aws secretsmanager get-secret-value \
  --secret-id co-intelligence-secrets \
  --region "$AWS_REGION" \
  --query SecretString \
  --output text)

DB_USER=$(echo "$SECRETS_JSON" | jq -r '.username // .DB_USERNAME')
DB_PASS=$(echo "$SECRETS_JSON" | jq -r '.password // .DB_PASSWORD')

if [[ -z "${DB_USER:-}" || -z "${DB_PASS:-}" || "${DB_USER}" == "null" || "${DB_PASS}" == "null" ]]; then
  echo "Failed to read DB credentials from secret 'co-intelligence-secrets'." >&2
  exit 1
fi

POD_NAME="rds-psql-$(date +%s)"

kubectl run -it --rm "$POD_NAME" \
  --namespace "$NAMESPACE" \
  --image "$PSQL_IMAGE" \
  --restart=Never \
  --env "PGPASSWORD=$DB_PASS" \
  -- psql -h "$RDS_ENDPOINT" -U "$DB_USER" -d "$DB_NAME" -p 5432 "sslmode=require"
