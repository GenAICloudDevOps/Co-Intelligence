# AWS Account ID Configuration

## Where Account ID is Used

### 1. Kubernetes Deployment Files (Auto-replaced by deploy.sh)
- `k8s/backend-deployment.yaml` - Line with `image:`
- `k8s/frontend-deployment.yaml` - Line with `image:`

**Format:**
```yaml
image: <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/co-intelligence-backend:latest
image: <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/co-intelligence-frontend:latest
```

### 2. Deploy Script (Automatic)
The `deploy.sh` script automatically replaces `<ACCOUNT_ID>` with your actual AWS account ID:

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
sed -i.bak "s/<ACCOUNT_ID>/$ACCOUNT_ID/g" k8s/backend-deployment.yaml
sed -i.bak "s/<ACCOUNT_ID>/$ACCOUNT_ID/g" k8s/frontend-deployment.yaml
```

## Manual Replacement (if needed)

```bash
# Get your AWS account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Replace in deployment files
sed -i "s/<ACCOUNT_ID>/$ACCOUNT_ID/g" k8s/backend-deployment.yaml
sed -i "s/<ACCOUNT_ID>/$ACCOUNT_ID/g" k8s/frontend-deployment.yaml
```

## Important Notes

1. **Always use `<ACCOUNT_ID>` placeholder** in the deployment YAML files
2. **Never commit actual account IDs** to version control
3. The `deploy.sh` script handles replacement automatically
4. Backup files (`.bak`) are created during replacement

## Verification

```bash
# Check current account ID
aws sts get-caller-identity --query Account --output text

# Verify deployment files
grep "image:" k8s/backend-deployment.yaml k8s/frontend-deployment.yaml
```
