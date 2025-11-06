# Code Execution Feature

## Overview

Co-Intelligence supports **autonomous code execution** - the AI can automatically run Python code when needed to answer your questions.

## How It Works

1. **User asks a question** that requires computation
2. **AI decides** if code execution is needed
3. **AI generates Python code** automatically
4. **Lambda executes** the code securely
5. **AI uses the result** to provide the answer

## Examples

### Math Calculations
```
User: "What's 15% of 2847?"
AI: [Executes code] → "15% of 2847 is 427.05"
```

### Data Analysis
```
User: "Find the sum of first 100 prime numbers"
AI: [Executes code] → "The sum is 24,133"
```

### Complex Logic
```
User: "Generate Fibonacci sequence up to 100"
AI: [Executes code] → Shows the sequence
```

## Architecture

```
User Question
    ↓
Gemini AI (with function calling)
    ↓
[Decides to execute code]
    ↓
AWS Lambda (co-intelligence-code-executor)
    ↓
Returns output
    ↓
AI formulates final answer
```

## Security

- ✅ **Sandboxed execution** - Code runs in isolated Lambda
- ✅ **Whitelisted modules** - Only safe Python modules allowed (math, json, datetime, random, statistics, re, collections, itertools, string, decimal, fractions, uuid, hashlib, base64, textwrap)
- ✅ **Custom __import__** - Blocks dangerous modules (os, sys, subprocess)
- ✅ **30-second timeout** - Prevents infinite loops
- ✅ **512MB memory limit** - Prevents resource exhaustion
- ✅ **No network access** - Lambda has no internet
- ✅ **No file system** - Cannot read/write files

## Allowed Python Modules

**Safe modules:**
- `math` - Mathematical functions
- `json` - JSON encoding/decoding
- `datetime` - Date and time operations
- `random` - Random number generation
- `statistics` - Statistical functions
- `re` - Regular expressions
- `collections` - Container datatypes
- `itertools` - Iterator functions
- `string` - String operations
- `decimal` - Decimal arithmetic
- `fractions` - Rational numbers
- `uuid` - UUID generation
- `hashlib` - Secure hashes
- `base64` - Base64 encoding
- `textwrap` - Text wrapping

**Blocked modules:**
- `os`, `sys`, `subprocess` - System access
- `socket`, `urllib`, `requests` - Network access
- `pickle`, `shelve` - Serialization (security risk)
- Any other non-whitelisted modules

## Cost

- **~$0.0000002 per execution**
- 1000 executions = **$0.0002** (~free)
- Very cost-effective!

## Deployment

### Initial Setup (One-time)

The Lambda function is created via CloudFormation:

```bash
cd infrastructure

aws cloudformation update-stack \
  --stack-name co-intelligence \
  --template-body file://infra_without_eks.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1

# Wait for completion (~5 minutes)
aws cloudformation wait stack-update-complete \
  --stack-name co-intelligence \
  --region us-east-1
```

### Verify Lambda Created

```bash
aws lambda get-function \
  --function-name co-intelligence-code-executor \
  --region us-east-1
```

### Update Backend

```bash
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

### Test

Open your Co-Intelligence chat and try:

1. **Simple test**: "What's 25 times 47?"
2. **Percentage**: "Calculate 15% of 2847"
3. **Complex**: "Generate first 10 Fibonacci numbers"
4. **With modules**: "What's the square root of 144?" (uses math module)

You should see:
- 🔄 *Executing code...*
- Code block
- Output
- AI's final answer

## Limitations

- Only works with **Gemini** model (Groq/Bedrock don't support function calling yet)
- Python only (no JavaScript, Java, etc.)
- Limited to whitelisted modules (no pip packages)
- 30-second execution timeout
- 512MB memory limit

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

### Module import errors
If you see "ModuleNotFoundError", the module is either:
1. Not in the whitelist (add to `SAFE_MODULES` in Lambda)
2. Blocked for security reasons (os, sys, subprocess)

### Still not working?
1. Verify you're using **Gemini** model (not Groq/Bedrock)
2. Check backend pod is running: `kubectl get pods`
3. Restart backend: `kubectl rollout restart deployment/backend`

## Disable Code Execution

To disable (if needed), update `agent.py`:

```python
async def stream_model(..., code_execution_enabled: bool = False):
```

Then redeploy backend.

## Success Indicators

✅ CloudFormation update complete  
✅ Lambda function exists  
✅ Backend pods running  
✅ Test queries execute code  
✅ Results shown in chat  
✅ Safe modules working (math, datetime, etc.)  
✅ Unsafe modules blocked (os, sys)  

## Time Required

- CloudFormation update: ~5 minutes
- Backend rebuild/deploy: ~3 minutes
- Testing: ~2 minutes

**Total: ~10 minutes**
