# RDS SSL Configuration Fix

## Problem
RDS PostgreSQL was enforcing SSL connections with self-signed certificates, causing backend pods to crash with:
```
ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self-signed certificate in certificate chain
```

## Solution

### 1. CloudFormation Template (Permanent Fix)
**File**: `infrastructure/infra_without_eks.yaml`

Added custom DB parameter group to disable SSL requirement:

```yaml
RDSParameterGroup:
  Type: AWS::RDS::DBParameterGroup
  Properties:
    DBParameterGroupName: co-intelligence-pg
    Description: Parameter group to disable SSL requirement
    Family: postgres17
    Parameters:
      rds.force_ssl: '0'
    Tags:
      - Key: Name
        Value: co-intelligence-pg

RDSInstance:
  Type: AWS::RDS::DBInstance
  Properties:
    # ... other properties ...
    DBParameterGroupName: !Ref RDSParameterGroup
```

### 2. Backend Code (Temporary Workaround - Now Removed)
**File**: `backend/main.py`

The SSL workaround code has been removed since the CloudFormation fix handles it properly:

```python
# REMOVED - No longer needed with proper RDS configuration
# import os
# import ssl
# os.environ['PGSSLMODE'] = 'prefer'
# ssl._create_default_https_context = ssl._create_unverified_context
```

### 3. Database URL
**Kubernetes Secret**: `app-secrets`

Simple connection string without SSL parameters:
```
postgres://cointelligence:SecurePass123!@co-intelligence-db.canq082qer4q.us-east-1.rds.amazonaws.com:5432/postgres
```

## For New Deployments

### Option A: Use Updated CloudFormation Template (Recommended)
```bash
aws cloudformation create-stack \
  --stack-name co-intelligence \
  --template-body file://infrastructure/infra_without_eks.yaml \
  --parameters ParameterKey=DBUsername,ParameterValue=cointelligence \
               ParameterKey=DBPassword,ParameterValue=YourSecurePassword123 \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --region us-east-1
```

The RDS instance will be created with SSL disabled from the start.

### Option B: Update Existing RDS Instance
```bash
# Create parameter group
aws rds create-db-parameter-group \
  --db-parameter-group-name co-intelligence-pg \
  --db-parameter-group-family postgres17 \
  --description "Disable SSL requirement" \
  --region us-east-1

# Modify parameter
aws rds modify-db-parameter-group \
  --db-parameter-group-name co-intelligence-pg \
  --parameters "ParameterName=rds.force_ssl,ParameterValue=0,ApplyMethod=immediate" \
  --region us-east-1

# Apply to RDS instance
aws rds modify-db-instance \
  --db-instance-identifier co-intelligence-db \
  --db-parameter-group-name co-intelligence-pg \
  --apply-immediately \
  --region us-east-1

# Reboot to apply changes
aws rds reboot-db-instance \
  --db-instance-identifier co-intelligence-db \
  --region us-east-1
```

## Verification

```bash
# Check parameter group
aws rds describe-db-parameters \
  --db-parameter-group-name co-intelligence-pg \
  --query "Parameters[?ParameterName=='rds.force_ssl']" \
  --region us-east-1

# Check RDS instance
aws rds describe-db-instances \
  --db-instance-identifier co-intelligence-db \
  --query 'DBInstances[0].DBParameterGroups' \
  --region us-east-1
```

## Important Notes

1. **Security**: Disabling SSL is acceptable for private VPC connections but not recommended for public endpoints
2. **Current Setup**: RDS is in private subnet, only accessible from EKS cluster
3. **Alternative**: If SSL is required, use proper certificate verification with AWS RDS CA bundle
4. **Production**: Consider using AWS Secrets Manager for database credentials

## Files Modified

- ✅ `infrastructure/infra_without_eks.yaml` - Added RDSParameterGroup
- ✅ `backend/main.py` - Removed SSL workaround (clean code)
- ✅ Kubernetes secret `app-secrets` - Simple DATABASE_URL without SSL params
