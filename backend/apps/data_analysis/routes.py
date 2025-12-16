from __future__ import annotations

import os
import time
import uuid
from typing import Any, Optional

import asyncio

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from botocore.exceptions import ClientError

from auth.models import User
from auth.utils import get_current_user
from config import settings
from services.file_service import validate_file
from services.streaming import create_sse_response, sse_event
from apps.data_analysis.aws_clients import DataAnalysisAWSClients, DataAnalysisAWSNotConfigured
from apps.data_analysis.graph import create_data_analysis_graph
from apps.data_analysis.models import DataAnalysisDataset, DataAnalysisRun

router = APIRouter()
graph = create_data_analysis_graph()


def _require_bucket() -> str:
    if not settings.S3_BUCKET_NAME:
        raise HTTPException(status_code=400, detail="S3_BUCKET_NAME not configured")
    return settings.S3_BUCKET_NAME


def _dataset_prefix(user_id: int, dataset_id: int) -> str:
    return f"data-analysis/user={user_id}/dataset={dataset_id}"


def _guess_format(filename: str) -> str:
    ext = os.path.splitext(filename or "")[1].lower()
    if ext in (".csv",):
        return "csv"
    if ext in (".json",):
        return "json"
    if ext in (".parquet",):
        return "parquet"
    # Glue ETL script supports limited formats by default
    return "csv"


class CreateS3SourceRequest(BaseModel):
    name: str
    s3_uri: str
    format: Optional[str] = None


class CreatePostgresSourceRequest(BaseModel):
    name: str
    schema: str = "public"
    table: str
    query: Optional[str] = None


class StartRunRequest(BaseModel):
    dataset_id: int
    message: Optional[str] = None
    # Optional override; when absent, pipeline runs "identity" conversion + catalog
    transformation_spec: Optional[dict[str, Any]] = None


class ChatRequest(BaseModel):
    message: str
    dataset_id: int
    model: Optional[str] = "gemini-2.5-flash-lite"

async def _start_pipeline_run(
    *,
    dataset: DataAnalysisDataset,
    current_user: User,
    transformation_spec: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    spec = transformation_spec or _default_identity_spec(dataset)
    run = await DataAnalysisRun.create(
        user_id=current_user.id,
        dataset_id=dataset.id,
        status="started",
        transformation_spec=spec,
        aws_region=settings.AWS_REGION,
    )

    try:
        clients = DataAnalysisAWSClients()
        bucket = _require_bucket()
        spec_key = f"{_dataset_prefix(current_user.id, dataset.id)}/specs/run={run.id}.json"
        spec_s3_uri = f"s3://{bucket}/{spec_key}"
        clients.put_json_to_s3(spec_s3_uri, spec)

        curated_prefix = f"{_dataset_prefix(current_user.id, dataset.id)}/curated/run={run.id}/"
        curated_s3_uri = f"s3://{bucket}/{curated_prefix}"

        schema_s3_uri = f"s3://{bucket}/{_dataset_prefix(current_user.id, dataset.id)}/metadata/run={run.id}/schema.json"

        execution_name = f"data-analysis-run-{run.id}"
        execution_arn = clients.start_pipeline(
            name=execution_name,
            input_payload={
                "user_id": current_user.id,
                "dataset_id": dataset.id,
                "dataset_name": dataset.name,
                "glue_database": settings.DATA_ANALYSIS_GLUE_DATABASE,
                "glue_table": _sanitize_table_name(current_user.id, dataset.id),
                "spec_s3_uri": spec_s3_uri,
                "curated_s3_uri": curated_s3_uri,
                "schema_s3_uri": schema_s3_uri,
                "source": {
                    "type": dataset.source_type,
                    "raw_s3_uri": dataset.raw_s3_uri,
                    "source_config": dataset.source_config,
                },
            },
        )

        run.spec_s3_uri = spec_s3_uri
        run.execution_arn = execution_arn
        run.status = "running"
        await run.save()

        dataset.curated_s3_uri = curated_s3_uri
        dataset.glue_table = _sanitize_table_name(current_user.id, dataset.id)
        dataset.glue_database = settings.DATA_ANALYSIS_GLUE_DATABASE
        dataset.status = "processing"
        dataset.last_run_id = run.id
        await dataset.save()

        return {"run_id": run.id, "execution_arn": execution_arn}
    except Exception as e:
        run.status = "failed"
        await run.save()
        dataset.status = "failed"
        dataset.last_error = str(e)
        dataset.last_run_id = run.id
        await dataset.save()
        raise


def _extract_state_name(event: dict[str, Any]) -> Optional[str]:
    for key in (
        "stateEnteredEventDetails",
        "stateExitedEventDetails",
        "taskStateEnteredEventDetails",
        "taskStateExitedEventDetails",
        "choiceStateEnteredEventDetails",
        "choiceStateExitedEventDetails",
        "parallelStateEnteredEventDetails",
        "parallelStateExitedEventDetails",
        "passStateEnteredEventDetails",
        "passStateExitedEventDetails",
        "mapStateEnteredEventDetails",
        "mapStateExitedEventDetails",
        "failStateEnteredEventDetails",
        "succeedStateEnteredEventDetails",
    ):
        details = event.get(key)
        if isinstance(details, dict) and details.get("name"):
            return details.get("name")
    return None


def _summarize_history_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summarized: list[dict[str, Any]] = []
    for e in events:
        item: dict[str, Any] = {
            "id": e.get("id"),
            "previous_event_id": e.get("previousEventId"),
            "timestamp": e.get("timestamp").isoformat() if getattr(e.get("timestamp"), "isoformat", None) else e.get("timestamp"),
            "type": e.get("type"),
            "state_name": _extract_state_name(e),
        }
        detail_key_by_type = {
            "ExecutionFailed": "executionFailedEventDetails",
            "ExecutionAborted": "executionAbortedEventDetails",
            "ExecutionTimedOut": "executionTimedOutEventDetails",
            "TaskFailed": "taskFailedEventDetails",
            "TaskTimedOut": "taskTimedOutEventDetails",
            "TaskAborted": "taskAbortedEventDetails",
            "LambdaFunctionFailed": "lambdaFunctionFailedEventDetails",
            "ActivityFailed": "activityFailedEventDetails",
        }
        detail_key = detail_key_by_type.get(e.get("type"))
        if detail_key:
            details = e.get(detail_key) or {}
            if isinstance(details, dict):
                item["error"] = details.get("error")
                item["cause"] = details.get("cause")
        summarized.append(item)
    return summarized


@router.get("/datasets")
async def list_datasets(current_user: User = Depends(get_current_user)):
    datasets = await DataAnalysisDataset.filter(user_id=current_user.id).order_by("-created_at").all()
    return {
        "datasets": [
            {
                "id": d.id,
                "name": d.name,
                "source_type": d.source_type,
                "status": d.status,
                "glue_database": d.glue_database,
                "glue_table": d.glue_table,
                "last_run_id": d.last_run_id,
                "created_at": d.created_at.isoformat(),
            }
            for d in datasets
        ]
    }


@router.get("/datasets/{dataset_id}")
async def get_dataset(dataset_id: int, current_user: User = Depends(get_current_user)):
    dataset = await DataAnalysisDataset.get_or_none(id=dataset_id, user_id=current_user.id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {
        "id": dataset.id,
        "name": dataset.name,
        "description": dataset.description,
        "source_type": dataset.source_type,
        "source_config": dataset.source_config,
        "raw_s3_uri": dataset.raw_s3_uri,
        "curated_s3_uri": dataset.curated_s3_uri,
        "glue_database": dataset.glue_database,
        "glue_table": dataset.glue_table,
        "status": dataset.status,
        "last_error": dataset.last_error,
        "last_run_id": dataset.last_run_id,
        "created_at": dataset.created_at.isoformat(),
    }


@router.get("/datasets/{dataset_id}/suggestions")
async def get_dataset_suggestions(dataset_id: int, current_user: User = Depends(get_current_user)):
    dataset = await DataAnalysisDataset.get_or_none(id=dataset_id, user_id=current_user.id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if not dataset.glue_database or not dataset.glue_table:
        raise HTTPException(status_code=400, detail="Dataset not ready")
    try:
        clients = DataAnalysisAWSClients()
        schema = clients.get_table_schema(dataset.glue_database, dataset.glue_table)
        cols = [c["name"] for c in schema]
        
        from services.ai_service import ai_service
        prompt = f"""Given a dataset with columns: {', '.join(cols)}
Generate exactly 4 short analytical questions a user might ask. Return as JSON array of strings only.
Example: ["What is total revenue by region?", "Show top 5 customers"]"""
        
        response = await ai_service.generate_response(prompt, "gemini-2.5-flash-lite")
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")[1:-1]
            response = "\n".join(lines)
        
        import json
        suggestions = json.loads(response)
        return {"suggestions": suggestions[:4]}
    except Exception as e:
        return {"suggestions": [
            f"Show total count of records",
            f"What are the top 5 {cols[0] if cols else 'items'}?",
            f"Show summary statistics",
            f"List unique values in {cols[-1] if cols else 'column'}"
        ]}


@router.post("/datasets/{dataset_id}/export")
async def export_dataset_query(dataset_id: int, request: ChatRequest, current_user: User = Depends(get_current_user)):
    from fastapi.responses import StreamingResponse
    import io
    import csv
    
    dataset = await DataAnalysisDataset.get_or_none(id=dataset_id, user_id=current_user.id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if not dataset.glue_database or not dataset.glue_table:
        raise HTTPException(status_code=400, detail="Dataset not ready")
    
    try:
        clients = DataAnalysisAWSClients()
        result = await clients.run_athena_query_async(
            sql=request.message,
            database=dataset.glue_database,
            timeout_seconds=120.0,
            max_rows=1000
        )
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(result.columns)
        writer.writerows(result.rows)
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={dataset.name}_export.csv"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/datasets/{dataset_id}/preview")
async def get_dataset_preview(dataset_id: int, limit: int = 5, current_user: User = Depends(get_current_user)):
    dataset = await DataAnalysisDataset.get_or_none(id=dataset_id, user_id=current_user.id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if not dataset.glue_database or not dataset.glue_table:
        raise HTTPException(status_code=400, detail="Dataset not ready for preview")
    try:
        clients = DataAnalysisAWSClients()
        sql = f"SELECT * FROM {dataset.glue_database}.{dataset.glue_table} LIMIT {min(limit, 50)}"
        result = await clients.run_athena_query_async(sql=sql, database=dataset.glue_database, timeout_seconds=60.0, max_rows=min(limit, 50))
        return {"columns": result.columns, "rows": result.rows}
    except DataAnalysisAWSNotConfigured as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/datasets/{dataset_id}/schema")
async def get_dataset_schema(dataset_id: int, current_user: User = Depends(get_current_user)):
    dataset = await DataAnalysisDataset.get_or_none(id=dataset_id, user_id=current_user.id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if not dataset.glue_database or not dataset.glue_table:
        raise HTTPException(status_code=400, detail="Dataset schema not available yet")
    try:
        clients = DataAnalysisAWSClients()
        schema = clients.get_table_schema(dataset.glue_database, dataset.glue_table)
        return {"dataset_id": dataset.id, "columns": schema}
    except DataAnalysisAWSNotConfigured as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sources/upload")
async def upload_source(
    file: UploadFile = File(...),
    name: str = "Uploaded Dataset",
    auto_run: bool = True,
    current_user: User = Depends(get_current_user),
):
    try:
        content = await file.read()
        valid, error = validate_file(file.filename, len(content))
        if not valid:
            raise HTTPException(status_code=400, detail=error)

        dataset = await DataAnalysisDataset.create(
            user_id=current_user.id,
            name=name,
            source_type="upload",
            source_config={"filename": file.filename, "format": _guess_format(file.filename)},
            glue_database=settings.DATA_ANALYSIS_GLUE_DATABASE,
        )
        bucket = _require_bucket()
        key = f"{_dataset_prefix(current_user.id, dataset.id)}/raw/{uuid.uuid4()}-{os.path.basename(file.filename)}"
        raw_s3_uri = f"s3://{bucket}/{key}"

        clients = DataAnalysisAWSClients()
        clients.put_bytes_to_s3(raw_s3_uri, content)

        dataset.raw_s3_uri = raw_s3_uri
        dataset.status = "created"
        await dataset.save()

        response: dict[str, Any] = {"dataset_id": dataset.id, "raw_s3_uri": raw_s3_uri}
        if auto_run:
            run_info = await _start_pipeline_run(dataset=dataset, current_user=current_user)
            response.update(run_info)
        return response
    except DataAnalysisAWSNotConfigured as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        dataset.status = "failed"
        dataset.last_error = str(e)
        await dataset.save()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sources/s3")
async def create_s3_source(
    request: CreateS3SourceRequest,
    auto_run: bool = True,
    current_user: User = Depends(get_current_user),
):
    dataset = await DataAnalysisDataset.create(
        user_id=current_user.id,
        name=request.name,
        source_type="s3",
        source_config={"s3_uri": request.s3_uri, "format": request.format or "parquet"},
        raw_s3_uri=request.s3_uri,
        glue_database=settings.DATA_ANALYSIS_GLUE_DATABASE,
        status="created",
    )
    response: dict[str, Any] = {"dataset_id": dataset.id}
    if auto_run:
        try:
            run_info = await _start_pipeline_run(dataset=dataset, current_user=current_user)
            response.update(run_info)
        except DataAnalysisAWSNotConfigured as e:
            dataset.status = "failed"
            dataset.last_error = str(e)
            await dataset.save()
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            dataset.status = "failed"
            dataset.last_error = str(e)
            await dataset.save()
            raise HTTPException(status_code=500, detail=str(e))
    return response


@router.post("/sources/postgres")
async def create_postgres_source(
    request: CreatePostgresSourceRequest,
    auto_run: bool = True,
    current_user: User = Depends(get_current_user),
):
    dataset = await DataAnalysisDataset.create(
        user_id=current_user.id,
        name=request.name,
        source_type="postgres",
        source_config={"schema": request.schema, "table": request.table, "query": request.query},
        glue_database=settings.DATA_ANALYSIS_GLUE_DATABASE,
        status="created",
    )
    response: dict[str, Any] = {"dataset_id": dataset.id}
    if auto_run:
        try:
            run_info = await _start_pipeline_run(dataset=dataset, current_user=current_user)
            response.update(run_info)
        except DataAnalysisAWSNotConfigured as e:
            dataset.status = "failed"
            dataset.last_error = str(e)
            await dataset.save()
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            dataset.status = "failed"
            dataset.last_error = str(e)
            await dataset.save()
            raise HTTPException(status_code=500, detail=str(e))
    return response


def _default_identity_spec(dataset: DataAnalysisDataset) -> dict[str, Any]:
    src_cfg = dataset.source_config or {}
    src_format = src_cfg.get("format") or "csv"
    input_spec: dict[str, Any] = {"alias": "a", "dataset_id": dataset.id, "type": dataset.source_type}
    if dataset.source_type in ("upload", "s3"):
        input_spec.update({"s3_uri": dataset.raw_s3_uri, "format": src_format})
    if dataset.source_type == "postgres":
        input_spec.update({"schema": src_cfg.get("schema"), "table": src_cfg.get("table"), "query": src_cfg.get("query")})

    return {
        "version": 1,
        "output": {"name": dataset.name, "partition_by": []},
        "inputs": [input_spec],
        "steps": [],
        "quality": {"max_null_fraction": 1.0},
    }


@router.post("/runs")
async def start_run(request: StartRunRequest, current_user: User = Depends(get_current_user)):
    dataset = await DataAnalysisDataset.get_or_none(id=request.dataset_id, user_id=current_user.id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    try:
        return await _start_pipeline_run(dataset=dataset, current_user=current_user, transformation_spec=request.transformation_spec)
    except DataAnalysisAWSNotConfigured as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        dataset.status = "failed"
        dataset.last_error = str(e)
        await dataset.save()
        raise HTTPException(status_code=500, detail=str(e))


def _sanitize_table_name(user_id: int, dataset_id: int) -> str:
    return f"u_{user_id}_dataset_{dataset_id}".replace("-", "_")


@router.get("/runs/{run_id}")
async def get_run(run_id: int, current_user: User = Depends(get_current_user)):
    run = await DataAnalysisRun.get_or_none(id=run_id, user_id=current_user.id).prefetch_related("dataset")
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    payload: dict[str, Any] = {
        "id": run.id,
        "dataset_id": run.dataset_id,
        "status": run.status,
        "execution_arn": run.execution_arn,
        "created_at": run.created_at.isoformat(),
        "updated_at": run.updated_at.isoformat(),
    }

    if run.execution_arn:
        try:
            clients = DataAnalysisAWSClients()
            exec_info = clients.get_execution(run.execution_arn)
            exec_status = exec_info.get("status")
            payload["execution_status"] = exec_status
            payload["execution_start"] = exec_info.get("startDate").isoformat() if exec_info.get("startDate") else None
            payload["execution_stop"] = exec_info.get("stopDate").isoformat() if exec_info.get("stopDate") else None
            if exec_status in ("SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"):
                if exec_status == "SUCCEEDED":
                    run.status = "succeeded"
                    run.dataset.status = "ready"
                else:
                    run.status = "failed"
                    run.dataset.status = "failed"
                    run.dataset.last_error = exec_info.get("cause") or exec_info.get("error") or run.dataset.last_error
                await run.save()
                await run.dataset.save()
        except Exception:
            pass

    return payload


@router.get("/runs/{run_id}/history")
async def get_run_history(run_id: int, current_user: User = Depends(get_current_user)):
    run = await DataAnalysisRun.get_or_none(id=run_id, user_id=current_user.id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if not run.execution_arn:
        raise HTTPException(status_code=400, detail="Run is missing execution_arn")

    try:
        clients = DataAnalysisAWSClients()
        history: list[dict[str, Any]] = []
        next_token: Optional[str] = None
        while True:
            resp = clients.get_execution_history(run.execution_arn, next_token=next_token, max_results=200, reverse_order=False)
            history.extend(resp.get("events") or [])
            next_token = resp.get("nextToken")
            if not next_token:
                break
        return {"run_id": run.id, "execution_arn": run.execution_arn, "events": _summarize_history_events(history)}
    except DataAnalysisAWSNotConfigured as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ClientError as e:
        code = (e.response or {}).get("Error", {}).get("Code", "ClientError")
        msg = (e.response or {}).get("Error", {}).get("Message", str(e))
        raise HTTPException(
            status_code=403,
            detail=f"AWS permission error calling Step Functions history ({code}): {msg}. Ensure the backend AWS credentials allow states:GetExecutionHistory.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs/{run_id}/events")
async def stream_run_events(
    run_id: int,
    request: Request,
    since_id: int = 0,
    poll_seconds: float = 2.0,
    current_user: User = Depends(get_current_user),
):
    run = await DataAnalysisRun.get_or_none(id=run_id, user_id=current_user.id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if not run.execution_arn:
        raise HTTPException(status_code=400, detail="Run is missing execution_arn")

    async def _gen():
        last_id = int(since_id or 0)
        yield sse_event({"run_id": run.id, "execution_arn": run.execution_arn, "since_id": last_id}, event="init")

        try:
            clients = DataAnalysisAWSClients()
        except DataAnalysisAWSNotConfigured as e:
            yield sse_event({"error": str(e)}, event="error")
            return

        while True:
            if await request.is_disconnected():
                return
            try:
                resp = clients.get_execution_history(run.execution_arn, max_results=200, reverse_order=True)
                events = resp.get("events") or []
                events.sort(key=lambda x: x.get("id", 0))
                new_events = [e for e in events if int(e.get("id", 0) or 0) > last_id]
                if new_events:
                    summarized = _summarize_history_events(new_events)
                    for item in summarized:
                        last_id = max(last_id, int(item.get("id") or 0))
                        yield sse_event(item, event="event")
                else:
                    yield sse_event({"ts": int(time.time())}, event="heartbeat")
            except ClientError as e:
                code = (e.response or {}).get("Error", {}).get("Code", "ClientError")
                msg = (e.response or {}).get("Error", {}).get("Message", str(e))
                yield sse_event(
                    {
                        "error": f"AWS permission error calling Step Functions history ({code}): {msg}. Ensure the backend AWS credentials allow states:GetExecutionHistory."
                    },
                    event="error",
                )
                return
            except Exception as e:
                yield sse_event({"error": str(e)}, event="error")
                return

            await asyncio.sleep(max(0.5, float(poll_seconds)))

    return create_sse_response(_gen())


@router.post("/chat")
async def chat(request: ChatRequest, current_user: User = Depends(get_current_user)):
    dataset = await DataAnalysisDataset.get_or_none(id=request.dataset_id, user_id=current_user.id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if not dataset.glue_database or not dataset.glue_table:
        raise HTTPException(status_code=400, detail="Dataset not queryable yet (missing glue_database/glue_table)")

    state = {
        "user_id": current_user.id,
        "model": request.model,
        "message": request.message,
        "dataset_id": dataset.id,
        "dataset_name": dataset.name,
        "glue_database": dataset.glue_database,
        "glue_table": dataset.glue_table,
        "thoughts": [],
        "current_step": 0,
    }
    result = await graph.ainvoke(state)
    
    # Format agent steps for UI
    agent_steps = []
    for t in result.get("thoughts", []):
        agent_steps.append({
            "step": t.get("step"),
            "thought": t.get("thought", ""),
            "tool": t.get("tool", ""),
            "status": "completed"
        })
    
    return {
        "response": result.get("final_answer", ""),
        "sql": result.get("last_sql", ""),
        "agent_steps": agent_steps,
        "chart_data": result.get("chart_data"),
        "error": result.get("error"),
    }
