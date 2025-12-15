from __future__ import annotations

import json
import re
from typing import Any, Literal, Optional, TypedDict

from langgraph.graph import END, StateGraph

from services.ai_service import ai_service
from apps.data_analysis.aws_clients import DataAnalysisAWSClients, DataAnalysisAWSNotConfigured


class DataAnalysisState(TypedDict, total=False):
    user_id: int
    model: str
    message: str
    intent: str

    dataset_id: int
    dataset_name: str
    glue_database: str
    glue_table: str

    sql: str
    query_result: dict
    response: str
    error: str


def detect_intent(state: DataAnalysisState) -> DataAnalysisState:
    message = (state.get("message") or "").strip().lower()
    if any(word in message for word in ["transform", "join", "derived", "mask", "tokenize", "pipeline", "etl"]):
        state["intent"] = "plan_transform"
    else:
        state["intent"] = "query"
    return state


def _sanitize_identifier(value: str) -> str:
    value = (value or "").strip()
    value = re.sub(r"[^a-zA-Z0-9_]", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    if not value:
        return "dataset"
    if value[0].isdigit():
        value = f"d_{value}"
    return value.lower()


async def plan_transform(state: DataAnalysisState) -> DataAnalysisState:
    dataset_name = state.get("dataset_name") or "dataset"
    prompt = f"""You are a data engineering planner.

User message:
{state.get("message","")}

Target output dataset name:
{dataset_name}

Return ONLY valid JSON (no markdown), matching this schema:
{{
  "version": 1,
  "output": {{"name": "string", "partition_by": ["optional_col"]}},
  "inputs": [{{"alias":"a","dataset":"{dataset_name}"}}],
  "steps": [
    {{"type":"rename","mapping":{{"old":"new"}}}},
    {{"type":"cast","columns":{{"col":"string|int|double|timestamp|date|boolean"}}}},
    {{"type":"filter_sql","expr":"SQL boolean expression"}},
    {{"type":"dedupe","subset":["col"],"keep":"first"}},
    {{"type":"pii","mode":"tokenize|redact|drop","columns":["col"]}},
    {{"type":"join","left":"a","right":"b","how":"inner|left|right|full","on":[{{"left":"col","right":"col"}}]}}
  ],
  "quality": {{"max_null_fraction": 0.2}}
}}
"""
    model = state.get("model")
    text = await ai_service.generate_response(prompt, model)
    try:
        state["response"] = json.dumps(json.loads(text), indent=2)
    except Exception:
        state["response"] = text
    return state


async def plan_sql(state: DataAnalysisState) -> DataAnalysisState:
    db = state.get("glue_database") or ""
    table = state.get("glue_table") or ""
    prompt = f"""You are a senior data analyst. Generate Athena SQL for the user's question.

Constraints:
- Return ONLY SQL, no prose.
- Query only this table: {db}.{table}
- Limit results to 50 rows unless aggregating.

User question:
{state.get("message","")}
"""
    model = state.get("model")
    sql = (await ai_service.generate_response(prompt, model)).strip()
    state["sql"] = sql
    return state


async def run_query(state: DataAnalysisState) -> DataAnalysisState:
    try:
        clients = DataAnalysisAWSClients()
        result = clients.run_athena_query(
            sql=state.get("sql") or "",
            database=state.get("glue_database") or "",
            workgroup=None,
            timeout_seconds=90.0,
            max_rows=50,
        )
        state["query_result"] = {
            "query_execution_id": result.query_execution_id,
            "columns": result.columns,
            "rows": result.rows,
        }
        return state
    except DataAnalysisAWSNotConfigured as e:
        state["error"] = str(e)
        return state
    except Exception as e:
        state["error"] = str(e)
        return state


async def answer(state: DataAnalysisState) -> DataAnalysisState:
    if state.get("error"):
        state["response"] = f"Data Analysis pipeline/query error: {state['error']}"
        return state
    qr = state.get("query_result") or {}
    prompt = f"""You are a data analyst. Answer the user's question using ONLY the query results below.

Question:
{state.get("message","")}

Columns:
{qr.get("columns", [])}

Rows:
{qr.get("rows", [])}

Write a concise answer, and include any important caveats (e.g., limited rows)."""
    model = state.get("model")
    state["response"] = await ai_service.generate_response(prompt, model)
    return state


def route_intent(state: DataAnalysisState) -> Literal["plan_transform", "query"]:
    return state.get("intent") or "query"


def create_data_analysis_graph():
    workflow = StateGraph(DataAnalysisState)
    workflow.add_node("detect_intent", detect_intent)
    workflow.add_node("plan_transform", plan_transform)
    workflow.add_node("plan_sql", plan_sql)
    workflow.add_node("run_query", run_query)
    workflow.add_node("answer", answer)

    workflow.set_entry_point("detect_intent")
    workflow.add_conditional_edges(
        "detect_intent",
        route_intent,
        {"plan_transform": "plan_transform", "query": "plan_sql"},
    )
    workflow.add_edge("plan_transform", END)
    workflow.add_edge("plan_sql", "run_query")
    workflow.add_edge("run_query", "answer")
    workflow.add_edge("answer", END)

    return workflow.compile()

