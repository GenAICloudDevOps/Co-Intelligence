from __future__ import annotations

import asyncio
import time
from typing import Dict

from config import settings

from .session import TerminalSession


_SESSIONS: Dict[str, TerminalSession] = {}
_USER_SESSIONS: Dict[int, str] = {}
_LOCK = asyncio.Lock()
_CLEANUP_TASK: asyncio.Task | None = None


def _idle_timeout_seconds() -> int:
    value = getattr(settings, "TERMINAL_IDLE_TIMEOUT_SECONDS", 900)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 900


def _ensure_cleanup_loop() -> None:
    global _CLEANUP_TASK
    if _CLEANUP_TASK and not _CLEANUP_TASK.done():
        return
    loop = asyncio.get_running_loop()
    _CLEANUP_TASK = loop.create_task(_cleanup_loop())


async def _cleanup_loop() -> None:
    while True:
        await asyncio.sleep(15)
        timeout = _idle_timeout_seconds()
        if timeout <= 0:
            continue
        now = time.time()
        expired = []
        async with _LOCK:
            for session_id, session in _SESSIONS.items():
                if now - session.last_activity > timeout:
                    expired.append(session_id)
        for session_id in expired:
            await close_session(session_id)


async def create_session(user_id: int, cols: int, rows: int) -> TerminalSession:
    existing_session: TerminalSession | None = None
    async with _LOCK:
        existing_id = _USER_SESSIONS.pop(user_id, None)
        if existing_id:
            existing_session = _SESSIONS.pop(existing_id, None)

    if existing_session:
        await existing_session.close()

    session = TerminalSession(user_id=user_id, cols=cols, rows=rows)
    await session.start()

    async with _LOCK:
        _SESSIONS[session.id] = session
        _USER_SESSIONS[user_id] = session.id

    _ensure_cleanup_loop()
    return session


async def close_session(session_id: str) -> None:
    async with _LOCK:
        session = _SESSIONS.pop(session_id, None)
        if session and _USER_SESSIONS.get(session.user_id) == session_id:
            _USER_SESSIONS.pop(session.user_id, None)

    if session:
        await session.close()
