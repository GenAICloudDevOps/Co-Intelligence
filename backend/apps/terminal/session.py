from __future__ import annotations

import asyncio
import os
import pty
import shutil
import struct
import subprocess
import time
import uuid
from typing import Callable, Awaitable

import fcntl
import termios

from config import settings


PRIVATE_NETS = [
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "127.0.0.0/8",
    "169.254.0.0/16",
    "100.64.0.0/10",
]

PRIVATE_NETS_V6 = [
    "fc00::/7",
    "fe80::/10",
    "::1/128",
]


def _build_bootstrap_script(block_private: bool) -> str:
    lines: list[str] = [
        "set -e",
        "export DEBIAN_FRONTEND=noninteractive",
        "if ! command -v sudo >/dev/null 2>&1; then apt-get update && apt-get install -y sudo; fi",
        "if ! command -v iptables >/dev/null 2>&1; then apt-get update && apt-get install -y iptables; fi",
        "if ! command -v setpriv >/dev/null 2>&1; then apt-get update && apt-get install -y util-linux; fi",
        "if ! id -u terminal >/dev/null 2>&1; then useradd -m -s /bin/bash terminal; fi",
        'echo "terminal ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/terminal',
        "chmod 0440 /etc/sudoers.d/terminal",
    ]
    if block_private:
        for cidr in PRIVATE_NETS:
            lines.append(f"iptables -A OUTPUT -d {cidr} -j REJECT || true")
        lines.append("if command -v ip6tables >/dev/null 2>&1; then")
        for cidr in PRIVATE_NETS_V6:
            lines.append(f"  ip6tables -A OUTPUT -d {cidr} -j REJECT || true")
        lines.append("fi")
    lines.append(
        "if command -v setpriv >/dev/null 2>&1; then exec setpriv --bounding-set=-cap_net_admin --inh-caps=-cap_net_admin -- su - terminal; fi"
    )
    lines.append("exec su - terminal")
    return "\n".join(lines)


class TerminalSession:
    def __init__(self, user_id: int, cols: int = 80, rows: int = 24) -> None:
        self.id = uuid.uuid4().hex
        self.user_id = user_id
        self.cols = cols
        self.rows = rows
        self.container_name = f"coi-terminal-{self.id}"
        self.master_fd: int | None = None
        self.proc: subprocess.Popen | None = None
        self.last_activity = time.time()
        self.closed = False

    def _touch(self) -> None:
        self.last_activity = time.time()

    def _build_docker_command(self) -> list[str]:
        image = getattr(settings, "TERMINAL_IMAGE", "ubuntu:22.04") or "ubuntu:22.04"
        cpu_limit = str(getattr(settings, "TERMINAL_CPU", "1") or "1")
        memory_limit = str(getattr(settings, "TERMINAL_MEMORY", "1g") or "1g")
        pids_limit = str(getattr(settings, "TERMINAL_PIDS_LIMIT", 256) or 256)
        block_private = bool(getattr(settings, "TERMINAL_BLOCK_PRIVATE_NETS", True))

        cmd = [
            "docker",
            "run",
            "--rm",
            "--name",
            self.container_name,
            "-i",
            "-t",
            "--network",
            "bridge",
            "--hostname",
            "terminal",
            "--cpus",
            cpu_limit,
            "--memory",
            memory_limit,
            "--pids-limit",
            pids_limit,
            "-e",
            "TERM=xterm-256color",
            "-e",
            "DEBIAN_FRONTEND=noninteractive",
        ]
        if block_private:
            cmd += ["--cap-add", "NET_ADMIN"]
        cmd.append(image)
        cmd += ["bash", "-lc", _build_bootstrap_script(block_private)]
        return cmd

    async def start(self) -> None:
        if not shutil.which("docker"):
            raise RuntimeError("Docker CLI not available in backend container.")
        info = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        if info.returncode != 0:
            detail = (info.stderr or "").strip()
            raise RuntimeError(detail or "Docker daemon unavailable.")

        master_fd, slave_fd = pty.openpty()
        self.master_fd = master_fd
        self._set_winsize(slave_fd, self.rows, self.cols)

        cmd = self._build_docker_command()
        self.proc = subprocess.Popen(
            cmd,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
        )
        os.close(slave_fd)
        os.set_blocking(master_fd, False)
        self._touch()

    async def stream_output(self, on_output: Callable[[bytes], Awaitable[None]]) -> None:
        if self.master_fd is None:
            return
        loop = asyncio.get_running_loop()
        while True:
            try:
                data = await loop.run_in_executor(None, os.read, self.master_fd, 4096)
            except Exception:
                break
            if not data:
                break
            self._touch()
            await on_output(data)

    def write(self, data: str) -> None:
        if self.master_fd is None or self.closed:
            return
        if not data:
            return
        os.write(self.master_fd, data.encode("utf-8", errors="ignore"))
        self._touch()

    def resize(self, cols: int, rows: int) -> None:
        if self.master_fd is None or self.closed:
            return
        self.cols = cols
        self.rows = rows
        self._set_winsize(self.master_fd, rows, cols)
        self._touch()

    async def close(self) -> None:
        if self.closed:
            return
        self.closed = True

        if self.master_fd is not None:
            try:
                os.close(self.master_fd)
            except OSError:
                pass
            self.master_fd = None

        if self.proc is not None:
            await asyncio.to_thread(self._terminate_process)
            self.proc = None

        await asyncio.to_thread(self._cleanup_container)

    def _terminate_process(self) -> None:
        if not self.proc:
            return
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=5)

    def _cleanup_container(self) -> None:
        if not shutil.which("docker"):
            return
        subprocess.run(
            ["docker", "rm", "-f", self.container_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    @staticmethod
    def _set_winsize(fd: int, rows: int, cols: int) -> None:
        try:
            buf = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(fd, termios.TIOCSWINSZ, buf)
        except Exception:
            pass
