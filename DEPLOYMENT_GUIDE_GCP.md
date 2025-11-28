# Co-Intelligence GCP Deployment Guide

Deploy Co-Intelligence to Google Cloud Platform using GKE, Cloud SQL, and Artifact Registry.

## Prerequisites

- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) installed and configured
- [Terraform](https://www.terraform.io/downloads) >= 1.0
- Docker installed
- kubectl installed

## Quick Start (2 Steps)

### Step 1: Create Infrastructure

```bash
cd infrastructure/gcp

# Initialize Terraform
terraform init

# Create infrastructure (replace YOUR_PROJECT_ID)
terraform apply -var="project_id=YOUR_PROJECT_ID"
```

This creates:
- ✅ VPC with private subnets
- ✅ GKE Standard cluster (2-3 e2-medium nodes)
- ✅ Cloud SQL PostgreSQL (2 vCPU, 8GB RAM, 50GB SSD)
- ✅ Artifact Registry (backend + frontend repos)
- ✅ Cloud Storage bucket
- ✅ Secret Manager secrets (auto-generated DB password + SECRET_KEY)

**Time:** ~15-20 minutes

### Step 2: Deploy Application

```bash
cd ../..  # Back to project root
./deploy-gcp.sh
```

This will:
- ✅ Fetch Terraform outputs
- ✅ Generate `.env.gcp` with all config values
- ✅ Build and push Docker images to Artifact Registry
- ✅ Configure kubectl for GKE
- ✅ Create Kubernetes secrets
- ✅ Deploy backend and frontend pods
- ✅ Output the LoadBalancer URL

---

## Configuration

### Terraform Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `project_id` | (required) | GCP Project ID |
| `region` | `us-east1` | GCP region |
| `zone` | `us-east1-b` | GCP zone |
| `db_username` | `cointelligence` | Database username |
| `app_name` | `co-intelligence` | App name prefix |

### Custom Configuration

```bash
terraform apply \
  -var="project_id=my-project" \
  -var="region=us-west1" \
  -var="zone=us-west1-a"
```

---

## Resources Created

| Resource | Spec | Purpose |
|----------|------|---------|
| GKE Cluster | Standard, 2-3 e2-medium nodes | Kubernetes |
| Cloud SQL | PostgreSQL 15, 2 vCPU, 8GB RAM, 50GB | Database |
| Artifact Registry | 2 repos (backend, frontend) | Docker images |
| Cloud Storage | 1 bucket | File storage |
| Secret Manager | 2 secrets | DB password, SECRET_KEY |
| VPC | 1 network + subnet | Networking |

---

## Monitoring

```bash
# Check pods
kubectl get pods -n co-intelligence

# View backend logs
kubectl logs -f deployment/backend -n co-intelligence

# View frontend logs
kubectl logs -f deployment/frontend -n co-intelligence

# Check HPA status
kubectl get hpa -n co-intelligence

# Get external IP
kubectl get svc frontend -n co-intelligence
```

---

## Update Deployment

After code changes:

```bash
./deploy-gcp.sh
```

Or update only images:

```bash
# Rebuild and push
docker build -t $(terraform -chdir=infrastructure/gcp output -raw backend_registry)/backend:latest ./backend
docker push $(terraform -chdir=infrastructure/gcp output -raw backend_registry)/backend:latest

# Restart pods
kubectl rollout restart deployment/backend -n co-intelligence
```

---

## Cleanup

```bash
# Delete K8s resources
kubectl delete namespace co-intelligence

# Destroy infrastructure
cd infrastructure/gcp
terraform destroy -var="project_id=YOUR_PROJECT_ID"
```

---

## Troubleshooting

### Terraform errors

```bash
# Re-authenticate
gcloud auth application-default login

# Enable APIs manually if needed
gcloud services enable container.googleapis.com sqladmin.googleapis.com
```

### Pod not starting

```bash
kubectl describe pod <pod-name> -n co-intelligence
kubectl logs <pod-name> -n co-intelligence
```

### Database connection issues

Cloud SQL uses private IP. Ensure pods are in the same VPC:
```bash
kubectl exec -it deployment/backend -n co-intelligence -- nc -zv <DB_HOST> 5432
```

---

## Cost Estimate

| Resource | Monthly Cost (approx) |
|----------|----------------------|
| GKE (2 e2-medium) | ~$50 |
| Cloud SQL (db-custom-2-8192) | ~$100 |
| Artifact Registry | ~$5 |
| Cloud Storage | ~$1 |
| **Total** | **~$156/month** |

*Costs vary by usage. Use [GCP Pricing Calculator](https://cloud.google.com/products/calculator) for accurate estimates.*
