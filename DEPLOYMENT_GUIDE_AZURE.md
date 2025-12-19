# Co-Intelligence Azure Deployment Guide

Deploy Co-Intelligence to Microsoft Azure using AKS, Azure Database for PostgreSQL, and Container Registry.

## Prerequisites

- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) installed
- [Terraform](https://www.terraform.io/downloads) >= 1.0
- Docker installed
- kubectl installed
- Azure subscription with sufficient quota

> **Important:** Azure SDKs are commented out in `backend/requirements.txt` by default. Before deploying to Azure, uncomment the Azure SDK section in that file:
> ```
> azure-storage-blob>=12.19.0
> azure-identity>=1.15.0
> azure-mgmt-logic>=10.0.0
> pyodbc>=5.0.0
> ```

## Fresh Deployment

### Step 1: Authenticate & Configure Azure

```bash
# Login to Azure
az login

# Set subscription (if you have multiple)
az account set --subscription "YOUR_SUBSCRIPTION_ID"

# Verify
az account show
```

### Step 2: Prepare Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API keys:
# - GEMINI_API_KEY (from Google AI Studio)
# - GROQ_API_KEY
# - TAVILY_API_KEY
```

### Step 3: Clean Terraform State (if re-deploying)

```bash
cd infrastructure/azure
rm -f terraform.tfstate terraform.tfstate.backup
rm -rf .terraform .terraform.lock.hcl
```

### Step 4: Create Infrastructure

```bash
cd infrastructure/azure

# Initialize Terraform
terraform init

# Create infrastructure
terraform apply
```

This creates:
- ✅ Resource Group in East US 2
- ✅ Virtual Network with subnets
- ✅ AKS Cluster (2-3 Standard_B2s nodes)
- ✅ Azure Database for PostgreSQL Flexible Server (Standard_B2ms, v15)
- ✅ Azure Container Registry (Basic)
- ✅ Storage Account
- ✅ Key Vault with secrets

**Time:** ~15-20 minutes

### Step 5: Deploy Application

```bash
cd ../..  # Back to project root

# Make script executable
chmod +x deploy-azure.sh

# Deploy
./deploy-azure.sh
```

This will:
- ✅ Fetch Terraform outputs
- ✅ Update `.env` with infrastructure values
- ✅ Build and push Docker images to ACR
- ✅ Configure kubectl for AKS
- ✅ Create Kubernetes secrets
- ✅ Deploy backend and frontend pods
- ✅ Output the LoadBalancer URL

---

## Configuration

### Terraform Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `resource_group_name` | `co-intelligence-rg` | Azure resource group |
| `location` | `eastus2` | Azure region |
| `app_name` | `cointelligence` | App name prefix |
| `db_username` | `cointelligence` | Database username |

### Custom Configuration

```bash
terraform apply \
  -var="location=westus2" \
  -var="resource_group_name=my-rg"
```

---

## Resources Created

| Resource | Spec | Purpose |
|----------|------|---------|
| AKS Cluster | 2-3 Standard_B2s nodes | Kubernetes |
| PostgreSQL | Flexible Server, Standard_B2ms, v15 | Database |
| Container Registry | Basic tier | Docker images |
| Storage Account | Standard LRS | File storage |
| Key Vault | Standard | Secrets |
| Virtual Network | 10.0.0.0/16 | Networking |

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
./deploy-azure.sh
```

Or update only images:

```bash
# Get ACR name
ACR_SERVER=$(terraform -chdir=infrastructure/azure output -raw acr_login_server)

# Rebuild and push
docker build -t $ACR_SERVER/backend:latest ./backend
docker push $ACR_SERVER/backend:latest

# Restart pods
kubectl rollout restart deployment/backend -n co-intelligence
```

---

## Cleanup

```bash
# Delete K8s resources
kubectl delete namespace co-intelligence

# Destroy infrastructure
cd infrastructure/azure
terraform destroy
```

---

## Troubleshooting

### Terraform errors

```bash
# Re-authenticate
az login

# Check subscription
az account show

# Register providers if needed
az provider register --namespace Microsoft.ContainerService
az provider register --namespace Microsoft.DBforPostgreSQL
```

### Pod not starting

```bash
kubectl describe pod <pod-name> -n co-intelligence
kubectl logs <pod-name> -n co-intelligence
```

### Database connection issues

PostgreSQL uses private endpoint. Verify from within cluster:
```bash
kubectl exec -it deployment/backend -n co-intelligence -- nc -zv <DB_HOST> 5432
```

### ACR pull errors

```bash
# Verify AKS has ACR access
az aks check-acr --resource-group co-intelligence-rg --name cointelligence-aks --acr <acr-name>
```

---

## Cost Estimate

| Resource | Monthly Cost (approx) |
|----------|----------------------|
| AKS (2 Standard_B2s) | ~$60 |
| PostgreSQL (Standard_B2ms) | ~$50 |
| Container Registry (Basic) | ~$5 |
| Storage Account | ~$1 |
| **Total** | **~$116/month** |

*Costs vary by usage. Use [Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/) for accurate estimates.*
