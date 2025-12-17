from __future__ import annotations

import json
from typing import Any

import boto3
import requests

from config import settings


DEFAULT_LAMBDA_NAME = "co-intelligence-code-executor"


def execute_python(code: str, timeout: int = 30) -> dict[str, Any]:
    """Execute Python code using a configured HTTP endpoint or AWS Lambda (best-effort)."""
    executor = (getattr(settings, "CODE_EXECUTOR_URL", "") or "").strip()

    if executor:
        if executor.startswith("http://") or executor.startswith("https://"):
            try:
                response = requests.post(
                    executor,
                    json={"code": code, "timeout": timeout},
                    timeout=timeout + 5,
                )
                result = response.json() if response.content else {}
                return {
                    "success": bool(result.get("success", False)),
                    "output": result.get("output", ""),
                    "errors": result.get("errors"),
                }
            except Exception as exc:
                return {"success": False, "output": "", "errors": f"Code execution failed: {exc}"}

        # Treat as Lambda function name or ARN
        try:
            lambda_client = boto3.client("lambda", region_name=getattr(settings, "AWS_REGION", None) or None)
            response = lambda_client.invoke(
                FunctionName=executor,
                InvocationType="RequestResponse",
                Payload=json.dumps({"code": code, "timeout": timeout}),
            )
            result = json.loads(response["Payload"].read())
            body = json.loads(result.get("body", "{}"))
            return {
                "success": bool(body.get("success", False)),
                "output": body.get("output", ""),
                "errors": body.get("errors"),
            }
        except Exception as exc:
            return {"success": False, "output": "", "errors": f"Code execution failed: {exc}"}

    # No explicit executor configured: optionally fall back to AWS Lambda when running on AWS
    if getattr(settings, "CLOUD_PROVIDER", "aws").lower() != "aws":
        return {"success": False, "output": "", "errors": "Code execution not configured"}

    try:
        lambda_client = boto3.client("lambda", region_name=getattr(settings, "AWS_REGION", None) or None)
        response = lambda_client.invoke(
            FunctionName=DEFAULT_LAMBDA_NAME,
            InvocationType="RequestResponse",
            Payload=json.dumps({"code": code, "timeout": timeout}),
        )
        result = json.loads(response["Payload"].read())
        body = json.loads(result.get("body", "{}"))
        return {
            "success": bool(body.get("success", False)),
            "output": body.get("output", ""),
            "errors": body.get("errors"),
        }
    except Exception as exc:
        return {"success": False, "output": "", "errors": f"Code execution failed: {exc}"}

