from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Optional

import boto3

from config import settings


class DataAnalysisAWSNotConfigured(Exception):
    pass


def _require_aws() -> None:
    if not settings.AWS_REGION:
        raise DataAnalysisAWSNotConfigured("AWS region not configured")

def _configuration_hint() -> str:
    return (
        "Set DATA_ANALYSIS_STATE_MACHINE_ARN to your AWS Step Functions state machine ARN "
        "(CloudFormation output key: DataAnalysisStateMachineArn). "
        "If you deployed on AWS with deploy-aws.sh, this should be auto-populated into .env and the Kubernetes secret."
    )


def _require_state_machine() -> str:
    if not settings.DATA_ANALYSIS_STATE_MACHINE_ARN:
        raise DataAnalysisAWSNotConfigured(f"DATA_ANALYSIS_STATE_MACHINE_ARN not configured. {_configuration_hint()}")
    return settings.DATA_ANALYSIS_STATE_MACHINE_ARN


def _athena_output_s3_uri() -> str:
    if settings.DATA_ANALYSIS_ATHENA_OUTPUT_S3_URI:
        return settings.DATA_ANALYSIS_ATHENA_OUTPUT_S3_URI
    if settings.S3_BUCKET_NAME:
        return f"s3://{settings.S3_BUCKET_NAME}/data-analysis/athena_results/"
    raise DataAnalysisAWSNotConfigured("S3_BUCKET_NAME or DATA_ANALYSIS_ATHENA_OUTPUT_S3_URI must be set")


@dataclass(frozen=True)
class AthenaQueryResult:
    query_execution_id: str
    rows: list[list[str]]
    columns: list[str]


class DataAnalysisAWSClients:
    def __init__(self):
        _require_aws()
        self._region = settings.AWS_REGION
        self._sfn = boto3.client("stepfunctions", region_name=self._region)
        self._s3 = boto3.client("s3", region_name=self._region)
        self._athena = boto3.client("athena", region_name=self._region)

    @property
    def region(self) -> str:
        return self._region

    def put_json_to_s3(self, s3_uri: str, payload: dict[str, Any]) -> None:
        if not s3_uri.startswith("s3://"):
            raise ValueError("s3_uri must start with s3://")
        bucket, key = s3_uri.replace("s3://", "", 1).split("/", 1)
        self._s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(payload).encode("utf-8"))

    def put_bytes_to_s3(self, s3_uri: str, content: bytes) -> None:
        if not s3_uri.startswith("s3://"):
            raise ValueError("s3_uri must start with s3://")
        bucket, key = s3_uri.replace("s3://", "", 1).split("/", 1)
        self._s3.put_object(Bucket=bucket, Key=key, Body=content)

    def start_pipeline(self, name: str, input_payload: dict[str, Any]) -> str:
        state_machine_arn = _require_state_machine()
        resp = self._sfn.start_execution(
            stateMachineArn=state_machine_arn,
            name=name,
            input=json.dumps(input_payload),
        )
        return resp["executionArn"]

    def get_execution(self, execution_arn: str) -> dict[str, Any]:
        return self._sfn.describe_execution(executionArn=execution_arn)

    def get_execution_history(
        self,
        execution_arn: str,
        next_token: Optional[str] = None,
        max_results: int = 1000,
        reverse_order: bool = False,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "executionArn": execution_arn,
            "maxResults": max_results,
            "reverseOrder": reverse_order,
        }
        if next_token:
            kwargs["nextToken"] = next_token
        return self._sfn.get_execution_history(**kwargs)

    def run_athena_query(
        self,
        sql: str,
        database: str,
        workgroup: Optional[str] = None,
        poll_seconds: float = 1.0,
        timeout_seconds: float = 60.0,
        max_rows: int = 50,
    ) -> AthenaQueryResult:
        workgroup = workgroup or settings.DATA_ANALYSIS_ATHENA_WORKGROUP
        output_location = _athena_output_s3_uri()

        start = self._athena.start_query_execution(
            QueryString=sql,
            QueryExecutionContext={"Database": database},
            ResultConfiguration={"OutputLocation": output_location},
            WorkGroup=workgroup,
        )
        qid = start["QueryExecutionId"]

        deadline = time.time() + timeout_seconds
        while True:
            q = self._athena.get_query_execution(QueryExecutionId=qid)
            state = q["QueryExecution"]["Status"]["State"]
            if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
                break
            if time.time() > deadline:
                raise TimeoutError("Athena query timed out")
            time.sleep(poll_seconds)

        if state != "SUCCEEDED":
            reason = q["QueryExecution"]["Status"].get("StateChangeReason", "Unknown error")
            raise RuntimeError(f"Athena query failed: {state}: {reason}")

        result = self._athena.get_query_results(QueryExecutionId=qid, MaxResults=max_rows)
        rows = result["ResultSet"]["Rows"]
        header = [c.get("VarCharValue", "") for c in rows[0]["Data"]] if rows else []
        data_rows: list[list[str]] = []
        for row in rows[1:]:
            data_rows.append([d.get("VarCharValue", "") for d in row.get("Data", [])])

        return AthenaQueryResult(query_execution_id=qid, rows=data_rows, columns=header)
