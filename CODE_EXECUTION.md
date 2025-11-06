# Code Execution Feature

## Overview

Co-Intelligence now supports **autonomous code execution** - the AI can automatically run Python code when needed to answer your questions.

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
- ✅ **Limited builtins** - Only safe Python functions allowed
- ✅ **30-second timeout** - Prevents infinite loops
- ✅ **512MB memory limit** - Prevents resource exhaustion
- ✅ **No network access** - Lambda has no internet
- ✅ **No file system** - Cannot read/write files
- ✅ **No imports** - Only built-in functions

## Allowed Python Functions

- Basic: `print`, `len`, `range`, `str`, `int`, `float`
- Collections: `list`, `dict`, `set`, `tuple`
- Math: `sum`, `max`, `min`, `abs`, `round`
- Iteration: `sorted`, `enumerate`, `zip`, `map`, `filter`
- Logic: `any`, `all`

## Cost

- **~$0.0000002 per execution**
- 1000 executions = **$0.0002** (~free)
- Very cost-effective!

## Deployment

### Initial Setup (One-time)

The Lambda function is created via CloudFormation:

```bash
# Lambda is included in infrastructure template
aws cloudformation update-stack \
  --stack-name co-intelligence \
  --template-body file://infrastructure/infra_without_eks.yaml \
  --capabilities CAPABILITY_NAMED_IAM
```

### Usage

No additional setup needed! The feature is automatically available when:
- Using **Gemini** model (supports function calling)
- Code execution is enabled (default: ON)

## Limitations

- Only works with **Gemini** model (Groq/Bedrock don't support function calling yet)
- Python only (no JavaScript, Java, etc.)
- Limited to built-in functions (no pip packages)
- 30-second execution timeout
- 512MB memory limit

## Future Enhancements

- [ ] Support for more languages (JavaScript, Java)
- [ ] Allow common libraries (numpy, pandas)
- [ ] User-controlled toggle in UI
- [ ] Show code execution history
- [ ] Code approval before execution (optional)

## Troubleshooting

### Code execution not working?

1. Check you're using **Gemini** model
2. Verify Lambda function exists: `aws lambda get-function --function-name co-intelligence-code-executor`
3. Check backend logs: `kubectl logs deployment/backend`
4. Verify IAM permissions for EKS nodes

### Lambda errors?

Check CloudWatch logs:
```bash
aws logs tail /aws/lambda/co-intelligence-code-executor --follow
```

## Disable Code Execution

To disable (if needed), update `agent.py`:

```python
async def stream_model(..., code_execution_enabled: bool = False):
```

Then redeploy backend.
