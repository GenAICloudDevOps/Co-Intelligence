# Deploy Code Execution Feature - Quick Guide

## Prerequisites
- Existing Co-Intelligence deployment
- AWS CLI configured
- kubectl configured for EKS cluster

## Step 1: Update CloudFormation Stack

```bash
cd infrastructure

aws cloudformation update-stack \
  --stack-name co-intelligence \
  --template-body file://infra_without_eks.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

**Wait for completion** (~5 minutes):
```bash
aws cloudformation wait stack-update-complete \
  --stack-name co-intelligence \
  --region us-east-1
```

## Step 2: Verify Lambda Created

```bash
aws lambda get-function \
  --function-name co-intelligence-code-executor \
  --region us-east-1
```

Expected output: Function details (not error)

## Step 3: Update Backend

```bash
cd ..
./update-backend.sh
```

Or manually:
```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

cd backend
docker build -t co-intelligence-backend .
docker tag co-intelligence-backend:latest $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/co-intelligence-backend:latest
docker push $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/co-intelligence-backend:latest

kubectl rollout restart deployment/backend
kubectl rollout status deployment/backend
```

## Step 4: Test

Open your Co-Intelligence chat and try:

1. **Simple test**: "What's 25 times 47?"
2. **Percentage**: "Calculate 15% of 2847"
3. **Complex**: "Generate first 10 Fibonacci numbers"

You should see:
- 🔄 *Executing code...*
- Code block
- Output
- AI's final answer

## Troubleshooting

### Lambda not found
```bash
# Check if Lambda exists
aws lambda list-functions --region us-east-1 | grep code-executor

# If not found, check CloudFormation
aws cloudformation describe-stack-events \
  --stack-name co-intelligence \
  --region us-east-1 | grep Lambda
```

### Backend can't invoke Lambda
```bash
# Check IAM permissions
aws iam get-role-policy \
  --role-name co-intelligence-eks-node-role \
  --policy-name LambdaInvokePolicy \
  --region us-east-1
```

### Code not executing
```bash
# Check backend logs
kubectl logs deployment/backend --tail=50

# Check Lambda logs
aws logs tail /aws/lambda/co-intelligence-code-executor --follow
```

### Still not working?
1. Verify you're using **Gemini** model (not Groq/Bedrock)
2. Check backend pod is running: `kubectl get pods`
3. Restart backend: `kubectl rollout restart deployment/backend`

## Rollback (if needed)

```bash
# Rollback CloudFormation
aws cloudformation cancel-update-stack \
  --stack-name co-intelligence \
  --region us-east-1

# Or delete Lambda manually
aws lambda delete-function \
  --function-name co-intelligence-code-executor \
  --region us-east-1
```

## Success Indicators

✅ CloudFormation update complete  
✅ Lambda function exists  
✅ Backend pods running  
✅ Test queries execute code  
✅ Results shown in chat  

## Time Required

- CloudFormation update: ~5 minutes
- Backend rebuild/deploy: ~3 minutes
- Testing: ~2 minutes

**Total: ~10 minutes**

## Cost Impact

- Lambda: ~$0.04 per 1000 executions
- Negligible cost increase

## Next Steps

After successful deployment:
1. Test various code execution scenarios
2. Monitor Lambda metrics in CloudWatch
3. Check for any errors in logs
4. Gather user feedback

See **CODE_EXECUTION.md** for full feature documentation.
