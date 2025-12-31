"""Docker-based code executor for AI Agent."""
from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import uuid


class AgentExecutor:
    """Manages a Docker container for AI agent code execution."""

    def __init__(self, session_id: str | None = None):
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self.container_name = f"ai-agent-{self.session_id}"
        self.container_running = False
        self.served_port: int | None = None

    async def ensure_container(self) -> None:
        """Start container if not running."""
        if self.container_running:
            return

        docker_path = shutil.which("docker")
        if not docker_path:
            raise RuntimeError("Docker not available")

        # Check if container exists
        result = subprocess.run(
            ["docker", "inspect", self.container_name],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            self.container_running = True
            return

        # Start new container with port for serving
        cmd = [
            "docker", "run", "-d",
            "--name", self.container_name,
            "--network", "bridge",
            "-w", "/workspace",
            "-e", "DEBIAN_FRONTEND=noninteractive",
            "ubuntu:22.04",
            "sleep", "3600",
        ]
        proc = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"Failed to start container: {proc.stderr}")

        # Install basics
        await self.run_command("apt-get update && apt-get install -y python3 python3-pip curl wget git nodejs npm")
        self.container_running = True

    async def run_command(self, command: str, timeout: int = 120) -> dict:
        """Execute command in container."""
        await self.ensure_container()

        cmd = ["docker", "exec", self.container_name, "bash", "-c", command]
        try:
            proc = await asyncio.wait_for(
                asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True),
                timeout=timeout,
            )
            return {
                "success": proc.returncode == 0,
                "stdout": proc.stdout[-4000:] if proc.stdout else "",
                "stderr": proc.stderr[-2000:] if proc.stderr else "",
                "exit_code": proc.returncode,
            }
        except asyncio.TimeoutError:
            return {"success": False, "stdout": "", "stderr": "Command timed out", "exit_code": -1}

    async def write_file(self, path: str, content: str) -> dict:
        """Write file in container."""
        await self.ensure_container()
        
        # Escape content for shell
        escaped = content.replace("\\", "\\\\").replace("'", "'\\''")
        cmd = f"mkdir -p $(dirname '{path}') && cat > '{path}' << 'EOFMARKER'\n{content}\nEOFMARKER"
        return await self.run_command(cmd)

    async def read_file(self, path: str) -> dict:
        """Read file from container."""
        return await self.run_command(f"cat '{path}'")

    async def serve_directory(self, directory: str = "/workspace", port: int = 8080) -> str | None:
        """Start HTTP server in container and return URL."""
        await self.ensure_container()

        # Kill any existing server
        await self.run_command("pkill -f 'python3 -m http.server' || true")

        # Start server in background
        cmd = f"cd {directory} && nohup python3 -m http.server {port} > /dev/null 2>&1 &"
        await self.run_command(cmd)

        # Get container IP
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}", self.container_name],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            ip = result.stdout.strip()
            self.served_port = port
            return f"http://{ip}:{port}"
        return None

    async def cleanup(self) -> None:
        """Stop and remove container."""
        if not shutil.which("docker"):
            return
        subprocess.run(
            ["docker", "rm", "-f", self.container_name],
            capture_output=True,
        )
        self.container_running = False


# Session storage
_executors: dict[str, AgentExecutor] = {}


def get_executor(session_id: str) -> AgentExecutor:
    """Get or create executor for session."""
    if session_id not in _executors:
        _executors[session_id] = AgentExecutor(session_id)
    return _executors[session_id]


async def cleanup_executor(session_id: str) -> None:
    """Cleanup executor for session."""
    if session_id in _executors:
        await _executors[session_id].cleanup()
        del _executors[session_id]
