"""Docker-based code executor for AI Agent."""
from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import uuid
from pathlib import Path


LOCAL_WORKSPACE_ROOT = os.environ.get("AI_AGENT_WORKSPACE_ROOT", "/tmp/ai-agent")


class AgentExecutor:
    """Manages a Docker container for AI agent code execution."""

    def __init__(self, session_id: str | None = None):
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self.container_name = f"ai-agent-{self.session_id}"
        self.container_running = False
        self.served_port: int | None = None
        self.host_port: int | None = None
        self.mode: str | None = None  # "docker" | "local"

    async def _ensure_mode(self) -> None:
        if self.mode:
            return
        if not shutil.which("docker"):
            self.mode = "local"
            return
        try:
            info = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=5,
            )
        except Exception:
            self.mode = "local"
            return
        self.mode = "docker" if info.returncode == 0 else "local"

    def _local_root(self) -> Path:
        return Path(LOCAL_WORKSPACE_ROOT) / self.session_id

    def _resolve_local_path(self, path: str) -> Path:
        if not path.startswith("/workspace"):
            raise ValueError("Only /workspace paths are supported")
        relative = path[len("/workspace"):].lstrip("/")
        base = self._local_root().resolve()
        target = (base / relative).resolve()
        if target != base and base not in target.parents:
            raise ValueError("Invalid path outside workspace")
        return target

    async def _write_local(self, path: str, content: str) -> dict:
        try:
            target = self._resolve_local_path(path)
            await asyncio.to_thread(target.parent.mkdir, parents=True, exist_ok=True)
            await asyncio.to_thread(target.write_text, content, encoding="utf-8")
            return {"success": True, "stdout": "", "stderr": "", "exit_code": 0}
        except Exception as exc:
            return {"success": False, "stdout": "", "stderr": str(exc), "exit_code": 1}

    async def _read_local(self, path: str) -> dict:
        try:
            target = self._resolve_local_path(path)
            if not target.exists() or not target.is_file():
                return {"success": False, "stdout": "", "stderr": "File not found", "exit_code": 1}
            content = await asyncio.to_thread(target.read_text, encoding="utf-8", errors="ignore")
            return {"success": True, "stdout": content, "stderr": "", "exit_code": 0}
        except Exception as exc:
            return {"success": False, "stdout": "", "stderr": str(exc), "exit_code": 1}

    async def ensure_container(self) -> None:
        """Start container if not running."""
        await self._ensure_mode()
        if self.mode != "docker":
            return
        if self.container_running:
            return

        # Check if container exists
        try:
            result = subprocess.run(
                ["docker", "inspect", self.container_name],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                self.container_running = True
                return
        except FileNotFoundError:
            self.mode = "local"
            return

        # Start new container with port for serving
        cmd = [
            "docker", "run", "-d",
            "--name", self.container_name,
            "--network", "bridge",
            "-p", "0:8080",
            "-w", "/workspace",
            "-e", "DEBIAN_FRONTEND=noninteractive",
            "ubuntu:22.04",
            "sleep", "3600",
        ]
        proc = await asyncio.to_thread(subprocess.run, cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            self.mode = "local"
            return

        # Install basics
        await self.run_command("apt-get update && apt-get install -y python3 python3-pip curl wget git nodejs npm")
        self.container_running = True

    async def run_command(self, command: str, timeout: int = 120) -> dict:
        """Execute command in container."""
        await self.ensure_container()
        if self.mode != "docker":
            return {
                "success": False,
                "stdout": "",
                "stderr": "Command execution unavailable (Docker not available)",
                "exit_code": 127,
            }

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
        await self._ensure_mode()
        if self.mode != "docker":
            return await self._write_local(path, content)
        await self.ensure_container()
        
        # Escape content for shell
        escaped = content.replace("\\", "\\\\").replace("'", "'\\''")
        cmd = f"mkdir -p $(dirname '{path}') && cat > '{path}' << 'EOFMARKER'\n{content}\nEOFMARKER"
        return await self.run_command(cmd)

    async def read_file(self, path: str) -> dict:
        """Read file from container."""
        await self._ensure_mode()
        if self.mode != "docker":
            return await self._read_local(path)
        return await self.run_command(f"cat '{path}'")

    async def serve_directory(self, directory: str = "/workspace", port: int = 8080) -> str | None:
        """Start HTTP server in container and return URL."""
        await self._ensure_mode()
        if self.mode != "docker":
            try:
                local_dir = self._resolve_local_path(directory)
                index_path = local_dir / "index.html"
                if not index_path.exists():
                    return None
                rel_path = index_path.relative_to(self._local_root().resolve()).as_posix()
                return f"/api/apps/ai-agent/sessions/{self.session_id}/files/{rel_path}"
            except Exception:
                return None
        await self.ensure_container()

        # Kill any existing server
        await self.run_command("pkill -f 'python3 -m http.server' || true")

        # Start server in background
        cmd = f"cd {directory} && nohup python3 -m http.server {port} > /dev/null 2>&1 &"
        await self.run_command(cmd)

        mapped = self._get_mapped_host_port(port)
        if mapped:
            host, host_port = mapped
            self.served_port = host_port
            self.host_port = host_port
            return f"http://{host}:{host_port}"

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

    def _get_mapped_host_port(self, port: int) -> tuple[str, int] | None:
        try:
            result = subprocess.run(
                ["docker", "port", self.container_name, str(port)],
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            return None
        if result.returncode != 0:
            return None
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            if "->" in line:
                line = line.split("->", 1)[-1].strip()
            host = "localhost"
            port_text = ""
            if line.startswith(":::"):
                port_text = line.split(":::", 1)[-1]
            elif line.startswith("[") and "]:" in line:
                host_part, port_text = line.rsplit("]:", 1)
                host = host_part[1:]
            elif ":" in line:
                host_part, port_text = line.rsplit(":", 1)
                host = host_part
            if host in ("0.0.0.0", "::", ":::"):
                host = "localhost"
            try:
                host_port = int(port_text)
            except ValueError:
                continue
            return host, host_port
        return None

    async def cleanup(self) -> None:
        """Stop and remove container."""
        if self.mode == "local":
            root = self._local_root()
            await asyncio.to_thread(shutil.rmtree, root, ignore_errors=True)
            return
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


def get_local_workspace(session_id: str) -> Path:
    """Return the local workspace root for a session (when Docker is unavailable)."""
    return Path(LOCAL_WORKSPACE_ROOT) / session_id


async def cleanup_executor(session_id: str) -> None:
    """Cleanup executor for session."""
    if session_id in _executors:
        await _executors[session_id].cleanup()
        del _executors[session_id]
