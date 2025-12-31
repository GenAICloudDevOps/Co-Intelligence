"""AI Agent with tools for code execution and file serving."""
from __future__ import annotations

import json
from services.ai_service import ai_service
from .executor import get_executor


SYSTEM_PROMPT = """You are a powerful AI agent that can answer questions AND take actions.

You have access to these tools (use JSON format to call them):
- run_command: Execute bash commands. Usage: {"tool": "run_command", "command": "..."}
- write_file: Create files. Usage: {"tool": "write_file", "path": "/workspace/...", "content": "..."}
- read_file: Read files. Usage: {"tool": "read_file", "path": "/workspace/..."}
- serve_website: Start HTTP server. Usage: {"tool": "serve_website", "directory": "/workspace"}

GUIDELINES:
- For simple questions: Answer directly WITHOUT using tools
- For tasks (build website, write code, etc.): Use tools by outputting the JSON on its own line
- Always use /workspace as the base directory
- After building a website, use serve_website to get a live URL
- Be concise but thorough"""


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


def extract_tool_calls(text: str) -> list[dict]:
    """Extract JSON tool calls from text."""
    tools = []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                data = json.loads(line)
                if "tool" in data:
                    tools.append(data)
            except json.JSONDecodeError:
                pass
    return tools


async def run_agent(session_id: str, user_message: str, history: list[dict] | None = None):
    """Run the agent with a user message."""
    # Build prompt
    prompt_parts = [SYSTEM_PROMPT, ""]
    
    if history:
        for msg in history[-6:]:  # Last 6 messages
            role = "User" if msg["role"] == "user" else "Assistant"
            prompt_parts.append(f"{role}: {msg['content']}")
    
    prompt_parts.append(f"User: {user_message}")
    prompt_parts.append("Assistant:")
    
    prompt = "\n".join(prompt_parts)
    
    served_url = None
    max_iterations = 3

    for _ in range(max_iterations):
        # Call AI (non-streaming for simplicity)
        try:
            response_text = await ai_service.call_model("gemini-2.5-flash", prompt)
        except Exception as e:
            return {"response": f"AI Error: {str(e)}", "served_url": None}

        # Check for tool calls
        tool_calls = extract_tool_calls(response_text)

        if not tool_calls:
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

    return {"response": response_text.strip(), "served_url": served_url}
