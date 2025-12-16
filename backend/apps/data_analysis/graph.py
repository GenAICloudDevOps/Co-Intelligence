from __future__ import annotations

import json
import re
from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from services.ai_service import ai_service
from apps.data_analysis.aws_clients import DataAnalysisAWSClients, DataAnalysisAWSNotConfigured


class AgentState(TypedDict, total=False):
    user_id: int
    model: str
    message: str
    dataset_id: int
    dataset_name: str
    glue_database: str
    glue_table: str
    
    # Agent state
    thoughts: list[dict]  # [{step, thought, tool, tool_input, observation}]
    current_step: int
    final_answer: str
    last_sql: str
    chart_data: dict  # {type, title, x_column, y_column, labels, values}
    error: str


TOOLS_DESCRIPTION = """You have these tools:

1. get_schema - Get column names and types for the dataset
   Input: none
   
2. run_sql - Execute SQL query on Athena
   Input: {"sql": "SELECT ..."}
   
3. sample_data - Get top 5 rows from the dataset
   Input: none

4. create_chart - Create a visualization from query results
   Input: {"type": "bar|line|pie", "title": "Chart title", "x_column": "column_name", "y_column": "column_name", "sql": "SELECT ..."}
   Use this for aggregations, trends, comparisons
   
5. answer - Provide final answer to user
   Input: {"answer": "Your answer here", "chart": optional chart config from create_chart}
"""

AGENT_PROMPT = """You are a data analyst agent. Answer the user's question about their dataset.

Database: {database}
Table: {table}

{tools}

IMPORTANT RULES:
- Always call get_schema first to know the columns
- Use exact column names from schema in SQL
- If SQL fails, read the error and fix it
- Limit queries to 50 rows unless aggregating
- After getting query results, call answer tool

Respond in this JSON format only:
{{"thought": "your reasoning", "tool": "tool_name", "tool_input": {{}}}}

User question: {question}

Previous steps:
{history}

What's your next step?"""


def _strip_markdown(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _format_history(thoughts: list[dict]) -> str:
    if not thoughts:
        return "None yet"
    lines = []
    for t in thoughts:
        lines.append(f"Step {t.get('step', '?')}:")
        lines.append(f"  Thought: {t.get('thought', '')}")
        lines.append(f"  Tool: {t.get('tool', '')} | Input: {t.get('tool_input', '')}")
        lines.append(f"  Observation: {t.get('observation', '')[:500]}")
    return "\n".join(lines)


async def agent_think(state: AgentState) -> AgentState:
    """Agent decides next action"""
    thoughts = state.get("thoughts") or []
    step = state.get("current_step", 0) + 1
    
    if step > 5:
        state["final_answer"] = "I couldn't complete the analysis within the allowed steps. Please try a simpler question."
        state["current_step"] = step
        return state
    
    prompt = AGENT_PROMPT.format(
        database=state.get("glue_database", ""),
        table=state.get("glue_table", ""),
        tools=TOOLS_DESCRIPTION,
        question=state.get("message", ""),
        history=_format_history(thoughts)
    )
    
    model = state.get("model")
    response = await ai_service.generate_response(prompt, model)
    response = _strip_markdown(response)
    
    try:
        parsed = json.loads(response)
        thought = parsed.get("thought", "")
        tool = parsed.get("tool", "")
        tool_input = parsed.get("tool_input", {})
    except:
        thought = response
        tool = "answer"
        tool_input = {"answer": response}
    
    new_thought = {
        "step": step,
        "thought": thought,
        "tool": tool,
        "tool_input": tool_input,
        "observation": ""
    }
    
    thoughts.append(new_thought)
    state["thoughts"] = thoughts
    state["current_step"] = step
    
    return state


async def execute_tool(state: AgentState) -> AgentState:
    """Execute the selected tool"""
    thoughts = state.get("thoughts") or []
    if not thoughts:
        return state
    
    current = thoughts[-1]
    tool = current.get("tool", "")
    tool_input = current.get("tool_input", {})
    observation = ""
    
    try:
        clients = DataAnalysisAWSClients()
        
        if tool == "get_schema":
            schema = clients.get_table_schema(
                state.get("glue_database", ""),
                state.get("glue_table", "")
            )
            observation = f"Columns: {json.dumps(schema)}"
            
        elif tool == "run_sql":
            sql = tool_input.get("sql", "")
            state["last_sql"] = sql
            result = await clients.run_athena_query_async(
                sql=sql,
                database=state.get("glue_database", ""),
                timeout_seconds=90.0,
                max_rows=50
            )
            observation = f"Columns: {result.columns}\nRows ({len(result.rows)}): {json.dumps(result.rows[:10])}"
            if len(result.rows) > 10:
                observation += f"\n... and {len(result.rows) - 10} more rows"
                
        elif tool == "sample_data":
            sql = f"SELECT * FROM {state.get('glue_database', '')}.{state.get('glue_table', '')} LIMIT 5"
            state["last_sql"] = sql
            result = await clients.run_athena_query_async(
                sql=sql,
                database=state.get("glue_database", ""),
                timeout_seconds=60.0,
                max_rows=5
            )
            observation = f"Columns: {result.columns}\nSample rows: {json.dumps(result.rows)}"

        elif tool == "create_chart":
            sql = tool_input.get("sql", "")
            state["last_sql"] = sql
            result = await clients.run_athena_query_async(
                sql=sql,
                database=state.get("glue_database", ""),
                timeout_seconds=90.0,
                max_rows=50
            )
            x_col = tool_input.get("x_column", result.columns[0] if result.columns else "x")
            y_col = tool_input.get("y_column", result.columns[1] if len(result.columns) > 1 else "y")
            x_idx = result.columns.index(x_col) if x_col in result.columns else 0
            y_idx = result.columns.index(y_col) if y_col in result.columns else 1
            
            state["chart_data"] = {
                "type": tool_input.get("type", "bar"),
                "title": tool_input.get("title", "Chart"),
                "x_column": x_col,
                "y_column": y_col,
                "labels": [row[x_idx] for row in result.rows],
                "values": [float(row[y_idx]) if row[y_idx] else 0 for row in result.rows]
            }
            observation = f"Chart created: {tool_input.get('type', 'bar')} chart with {len(result.rows)} data points"
            
        elif tool == "answer":
            state["final_answer"] = tool_input.get("answer", str(tool_input))
            observation = "Final answer provided"
            
        else:
            observation = f"Unknown tool: {tool}"
            
    except DataAnalysisAWSNotConfigured as e:
        observation = f"AWS Error: {e}"
    except Exception as e:
        observation = f"Error: {str(e)}"
    
    current["observation"] = observation
    state["thoughts"] = thoughts
    
    return state


def should_continue(state: AgentState) -> Literal["think", "end"]:
    """Check if agent should continue or stop"""
    if state.get("final_answer"):
        return "end"
    if state.get("current_step", 0) >= 5:
        return "end"
    return "think"


def format_response(state: AgentState) -> AgentState:
    """Format final response"""
    if not state.get("final_answer"):
        state["final_answer"] = "Unable to complete analysis."
    return state


def create_data_analysis_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("think", agent_think)
    workflow.add_node("execute", execute_tool)
    workflow.add_node("format", format_response)
    
    workflow.set_entry_point("think")
    workflow.add_edge("think", "execute")
    workflow.add_conditional_edges(
        "execute",
        should_continue,
        {"think": "think", "end": "format"}
    )
    workflow.add_edge("format", END)
    
    return workflow.compile()
