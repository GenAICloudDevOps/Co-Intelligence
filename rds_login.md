# RDS Login (PostgreSQL)

This RDS instance runs in private subnets, so the easiest way to connect is from inside EKS.

## Ops access note
This requires AWS credentials (Secrets Manager + CloudFormation) and Kubernetes access. It is intended for admins/ops, not end users.

## Namespace/RBAC guidance
Use a locked namespace (for example, `ops`) and limit who can create pods or exec into them. Treat any pod with DB credentials as sensitive.

## Option A: Login from EKS (recommended)

### 1) Fetch endpoint + credentials
```bash
RDS_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name co-intelligence \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`RDSEndpoint`].OutputValue' \
  --output text)

SECRETS_JSON=$(aws secretsmanager get-secret-value \
  --secret-id co-intelligence-secrets \
  --region us-east-1 \
  --query SecretString \
  --output text)

DB_USER=$(echo "$SECRETS_JSON" | jq -r '.username // .DB_USERNAME')
DB_PASS=$(echo "$SECRETS_JSON" | jq -r '.password // .DB_PASSWORD')
```

### 2) Start a temporary psql pod and connect
```bash
kubectl run -it --rm psql \
  --image=postgres:17 \
  --restart=Never \
  --env="PGPASSWORD=$DB_PASS" \
  -- psql -h "$RDS_ENDPOINT" -U "$DB_USER" -d postgres -p 5432 "sslmode=require"
```

### 3) Exit
- In psql: `\q`

## Option B: Login from your laptop (requires VPC access)
```bash
PGPASSWORD="$DB_PASS" psql \
  -h "$RDS_ENDPOINT" -U "$DB_USER" -d postgres -p 5432 \
  "sslmode=require"
```

Notes:
- Add `-n <namespace>` to the `kubectl run` command if your cluster uses a non-default namespace.
- If you use a bastion or VPN, ensure the security groups allow your source IP to reach port 5432.

## psql quick cheat sheet
- `\dt` list tables
- `\d <table>` describe a table
- `\x` toggle expanded output
- `\r` reset the current query buffer
- `\q` quit
- `\! clear` clear the screen
