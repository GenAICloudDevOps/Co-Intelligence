"""AI Agent with tools for code execution and file serving."""
from __future__ import annotations

import asyncio
import html as html_lib
import json
import re
from typing import Iterable
from urllib.parse import urlparse

from config import settings
from services.ai_service import ai_service
from services.guardrails import require_sources_footer
from services.web_search import search_web
from core.logging import get_logger
from .executor import get_executor


logger = get_logger("ai_agent")

SYSTEM_PROMPT = """You are a powerful AI agent that can answer questions AND take actions.

You have access to these tools (use JSON format to call them):
- run_command: Execute bash commands. Usage: {"tool": "run_command", "command": "..."}
- write_file: Create files. Usage: {"tool": "write_file", "path": "/workspace/...", "content": "..."}
- read_file: Read files. Usage: {"tool": "read_file", "path": "/workspace/..."}
- serve_website: Start HTTP server. Usage: {"tool": "serve_website", "directory": "/workspace"}

GUIDELINES:
- For simple questions: Answer directly WITHOUT using tools
- For tasks (build website, write code, etc.): Use tools by outputting the JSON on its own line
- For tool calls, emit a single-line JSON object with escaped newlines (\\n). Do NOT wrap in code fences.
- Always use /workspace as the base directory
- After building a website, use serve_website to get a live URL
- Be concise but thorough"""

_SITE_REQUEST_RE = re.compile(r"\b(html|website|web\s?page|landing|site|homepage|single[- ]page)\b", re.IGNORECASE)
_RESEARCH_REQUEST_RE = re.compile(
    r"\b(research|report|sources?|citations?|founder|funding|investigate|due diligence|everything you find|comprehensive)\b",
    re.IGNORECASE,
)
_GENERAL_QUESTION_RE = re.compile(r"^\s*(what|who|when|where|why|how|tell|explain|describe|define)\b", re.IGNORECASE)
_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_BUILD_VERB_RE = re.compile(r"\b(build|create|make|generate|design)\b", re.IGNORECASE)

WEB_RESEARCH_PROMPT = f"""You are a research analyst. Use ONLY the provided web search results.
Write a comprehensive, consolidated report with clear section headers (Executive Summary, Company Overview, Founders, Product, Funding, Market/Competition, Notes).
Use citation markers like [1], [2] that map to the sources list. Do not invent facts or sources.
{require_sources_footer()}"""

WEB_BUILDER_PROMPT = """You are a senior frontend engineer. Return a single complete HTML document.
Requirements:
- Start with <!doctype html> and include <html>, <head>, and <body>
- Use inline CSS and JS only (no external assets)
- Keep it simple, clean, and accessible
- Output ONLY the HTML document (no markdown, no code fences, no commentary)"""


async def execute_tool(session_id: str, tool_data: dict) -> tuple[str, str | None]:
    """Execute a tool and return result."""
    executor = get_executor(session_id)
    tool_name = tool_data.get("tool", "")
    served_url = None

    try:
        if tool_name == "run_command":
            result = await executor.run_command(tool_data.get("command", ""))
            output = result.get("stdout", "") or result.get("stderr", "")
            return f"[Output]\n{output[:2000]}" if output else "[No output]", None

        elif tool_name == "write_file":
            result = await executor.write_file(tool_data.get("path", ""), tool_data.get("content", ""))
            return "[File written]" if result["success"] else f"[Error: {result['stderr']}]", None

        elif tool_name == "read_file":
            result = await executor.read_file(tool_data.get("path", ""))
            if result["success"]:
                return f"[File Content]\n{result.get('stdout', '')}", None
            return f"[Error: {result.get('stderr', '')}]", None

        elif tool_name == "serve_website":
            directory = tool_data.get("directory", "/workspace")
            url = await executor.serve_directory(directory)
            if url:
                return f"[Server started at {url}]", url
            return "[Failed to start server]", None

    except Exception as e:
        return f"[Tool error: {str(e)}]", None

    return "[Unknown tool]", None


def _collect_tool_calls(candidate: str, tools: list[dict]) -> None:
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        return
    if isinstance(data, dict):
        if "tool" in data:
            tools.append(data)
        return
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and "tool" in item:
                tools.append(item)


def extract_tool_calls(text: str | None) -> list[dict]:
    """Extract JSON tool calls from text."""
    if not text:
        return []
    tools: list[dict] = []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            _collect_tool_calls(line, tools)

    for block in re.findall(r"```(?:json)?\s*([\s\S]*?)```", text):
        candidate = block.strip()
        if candidate:
            _collect_tool_calls(candidate, tools)
    return tools


def _format_history(history: Iterable[dict] | None) -> list[str]:
    if not history:
        return []
    formatted: list[str] = []
    for msg in list(history)[-6:]:
        if not isinstance(msg, dict):
            continue
        role = str(msg.get("role", "")).lower()
        content = msg.get("content")
        if content is None:
            continue
        role_label = "User" if role == "user" else "Assistant"
        formatted.append(f"{role_label}: {content}")
    return formatted


def _looks_like_site_request(message: str) -> bool:
    if not _SITE_REQUEST_RE.search(message):
        return False
    if _BUILD_VERB_RE.search(message):
        return True
    if "?" in message:
        return False
    if re.search(r"\b(what|where|who|when|why|how)\b", message, flags=re.IGNORECASE):
        return False
    return True


def _looks_like_web_research(message: str) -> bool:
    # If it's a general question, don't trigger web research
    if _GENERAL_QUESTION_RE.search(message):
        return False
    # Only trigger web research if there's a URL or explicit research keywords with context
    if _URL_RE.search(message):
        if _BUILD_VERB_RE.search(message) and _looks_like_site_request(message):
            return False
        return True
    # For "research" keyword, require additional context (founder, funding, etc.)
    if _RESEARCH_REQUEST_RE.search(message):
        # Check if it's a specific research request (not just "research about X")
        if re.search(r"\b(founder|funding|investigate|due diligence|comprehensive|report|sources?|citations?)\b", message, re.IGNORECASE):
            return True
    return False


def _extract_urls(text: str) -> list[str]:
    return [match.rstrip(").,;:!?\"'[]{}") for match in _URL_RE.findall(text)]


def _build_allow_urls(urls: Iterable[str]) -> list[str]:
    allow_urls: list[str] = []
    for url in urls:
        parsed = urlparse(url)
        host = (parsed.hostname or "").strip().lower()
        if not host:
            continue
        hosts = {host}
        if host.startswith("www."):
            hosts.add(host[4:])
        else:
            hosts.add(f"www.{host}")
        for h in hosts:
            for scheme in ("https", "http"):
                origin = f"{scheme}://{h}"
                if origin not in allow_urls:
                    allow_urls.append(origin)
    return allow_urls


def _format_search_results(results: list[dict]) -> str:
    lines: list[str] = []
    for idx, result in enumerate(results, 1):
        title = (result.get("title") or "").strip()
        url = (result.get("url") or "").strip()
        content = (result.get("content") or "").strip()
        if len(content) > 700:
            content = content[:697].rstrip() + "..."
        lines.append(f"[{idx}] {title}\nURL: {url}\n{content}")
    return "\n\n".join(lines)


def _fallback_html(text: str) -> str:
    escaped = html_lib.escape(text or "")
    return (
        "<!doctype html>\n<html>\n<head>\n<meta charset=\"utf-8\" />\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />\n"
        "<title>Generated Page</title>\n"
        "<style>body{font-family:Arial,Helvetica,sans-serif;padding:24px;}"
        "pre{white-space:pre-wrap;background:#f7f7f7;padding:16px;border-radius:8px;}"
        "</style>\n</head>\n<body>\n"
        "<h1>Generated Content</h1>\n"
        f"<pre>{escaped}</pre>\n"
        "</body>\n</html>"
    )


async def _run_web_research(
    message: str,
    model_name: str | None,
) -> dict:
    search_payload = await asyncio.to_thread(search_web, message, 4)
    results = search_payload.get("results") or []

    if not results:
        error = search_payload.get("error")
        if error:
            return {
                "response": (
                    "Web research is unavailable right now. "
                    f"Reason: {error}. "
                    "Configure TAVILY_API_KEY to enable live research."
                ),
                "served_url": None,
            }
        resolved_model = model_name or settings.AI_DEFAULT_MODEL
        fallback_prompt = (
            "You do not have live web access or search results. "
            "Provide a best-effort answer from general knowledge and clearly say that live research is unavailable.\n\n"
            f"User: {message}\nAssistant:"
        )
        response_text = await ai_service.call_model(resolved_model, fallback_prompt)
        return {"response": response_text.strip(), "served_url": None}

    search_context = _format_search_results(results)
    allow_urls = _build_allow_urls([r.get("url", "") for r in results] + _extract_urls(message))
    if not allow_urls:
        allow_urls = None
    resolved_model = model_name or settings.AI_DEFAULT_MODEL
    prompt = "\n".join(
        [
            WEB_RESEARCH_PROMPT,
            "",
            f"User Request: {message}",
            "",
            "Web Search Results:",
            search_context,
            "",
            "Assistant:",
        ]
    )
    response_text = await ai_service.generate_response(
        prompt,
        resolved_model,
        require_sources=True,
        allow_urls=allow_urls,
        block_pii=False,
    )
    return {"response": response_text.strip(), "served_url": None}


async def _run_site_builder(
    session_id: str,
    message: str,
    history: list[dict] | None,
    model_name: str | None,
) -> dict:
    prompt_parts = [WEB_BUILDER_PROMPT, ""]
    prompt_parts.extend(_format_history(history))
    prompt_parts.append(f"User: {message}")
    prompt_parts.append("Assistant:")
    prompt = "\n".join(prompt_parts)

    resolved_model = model_name or settings.AI_DEFAULT_MODEL
    try:
        response_text = await ai_service.call_model(resolved_model, prompt)
    except Exception as e:
        logger.exception("ai_agent_model_call_failed", extra={"session_id": session_id})
        return {"response": f"AI Error: {str(e)}", "served_url": None}
    
    if not isinstance(response_text, str):
        response_text = "" if response_text is None else str(response_text)
    if not response_text.strip():
        return {"response": "AI Error: Empty response from model.", "served_url": None}

    html = _extract_html(response_text) or _fallback_html(response_text)
    served_url = None
    serve_error: str | None = None

    try:
        executor = get_executor(session_id)
        write_result = await executor.write_file("/workspace/index.html", html)
        if write_result.get("success"):
            url = await executor.serve_directory("/workspace")
            if url:
                served_url = url
        else:
            serve_error = write_result.get("stderr") or "Failed to write file"
    except Exception as exc:
        serve_error = str(exc)

    if serve_error:
        html = f"{html}\n\n[Preview unavailable: {serve_error}]"

    return {"response": html.strip(), "served_url": served_url}

def _extract_html(text: str | None) -> str | None:
    if not text:
        return None
    
    # First check for code fences
    for block in re.findall(r"```(?:html)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE):
        candidate = block.strip()
        if "<html" in candidate.lower() or "<!doctype html" in candidate.lower():
            return candidate

    lowered = text.lower()
    start = lowered.find("<!doctype html")
    if start == -1:
        start = lowered.find("<html")
    if start == -1:
        return None

    end = lowered.rfind("</html>")
    if end != -1:
        return text[start:end + len("</html>")].strip()
    
    # If no closing tag, return from start to end
    return text[start:].strip()


async def run_agent(
    session_id: str,
    user_message: str,
    history: list[dict] | None = None,
    model_name: str | None = None,
):
    """Run the agent with a user message."""
    message = (user_message or "").strip()
    if not message:
        return {"response": "Please provide a message to continue.", "served_url": None}

    if _looks_like_web_research(message):
        try:
            return await _run_web_research(message, model_name)
        except Exception as exc:
            logger.exception("ai_agent_research_failed", extra={"session_id": session_id})
            return {"response": f"AI Error: {exc}", "served_url": None}

    if _looks_like_site_request(message):
        try:
            return await _run_site_builder(session_id, message, history, model_name)
        except Exception as exc:
            logger.exception("ai_agent_site_failed", extra={"session_id": session_id})
            return {"response": f"AI Error: {exc}", "served_url": None}

    # Build prompt
    prompt_parts = [SYSTEM_PROMPT, ""]

    prompt_parts.extend(_format_history(history))

    prompt_parts.append(f"User: {message}")
    prompt_parts.append("Assistant:")

    prompt = "\n".join(prompt_parts)

    served_url = None
    max_iterations = 3
    response_text = ""

    try:
        for _ in range(max_iterations):
            # Call AI (non-streaming for simplicity)
            try:
                resolved_model = model_name or settings.AI_DEFAULT_MODEL
                response_text = await ai_service.call_model(resolved_model, prompt)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                return {"response": f"AI Error: {str(e)}", "served_url": None}

            if not isinstance(response_text, str):
                response_text = "" if response_text is None else str(response_text)
            if not response_text.strip():
                return {"response": "AI Error: Empty response from model.", "served_url": None}

            # Check for tool calls
            tool_calls = extract_tool_calls(response_text)

            if not tool_calls:
                if _looks_like_site_request(message):
                    html = _extract_html(response_text)
                    if html:
                        try:
                            executor = get_executor(session_id)
                            write_result = await executor.write_file("/workspace/index.html", html)
                            if write_result.get("success"):
                                url = await executor.serve_directory("/workspace")
                                if url:
                                    served_url = url
                            else:
                                error = write_result.get("stderr") or "Failed to write file"
                                response_text = f"{response_text.strip()}\n\n[Auto-serve failed: {error}]"
                        except Exception as exc:
                            response_text = f"{response_text.strip()}\n\n[Auto-serve failed: {exc}]"
                return {"response": response_text.strip(), "served_url": served_url}

            # Execute tools
            tool_results = []
            for tool_data in tool_calls:
                result, url = await execute_tool(session_id, tool_data)
                tool_results.append(result)
                if url:
                    served_url = url

            # Add results to prompt for next iteration
            prompt += f" {response_text}\n\nTool Results:\n" + "\n".join(tool_results) + "\n\nAssistant:"
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.exception("ai_agent_failed", extra={"session_id": session_id})
        return {"response": f"AI Error: {exc}", "served_url": None}

    return {"response": response_text.strip(), "served_url": served_url}
