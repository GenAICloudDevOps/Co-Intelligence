"""Centralized streaming/SSE service"""
import json
import numpy as np
import pandas as pd
from typing import Any, AsyncGenerator
from fastapi.responses import StreamingResponse

def safe_serialize(data: Any) -> str:
    """Safely serialize data to JSON, handling numpy/pandas types"""
    def handler(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (np.int32, np.int64, np.float32, np.float64)):
            return float(obj) if 'float' in str(type(obj)) else int(obj)
        elif isinstance(obj, (pd.DataFrame, pd.Series)):
            return obj.to_dict()
        elif hasattr(obj, 'tolist'):
            return obj.tolist()
        elif hasattr(obj, 'item'):
            return obj.item()
        else:
            return str(obj)
    return json.dumps(data, default=handler)

def sse_event(data: dict, event: str = None) -> str:
    """Format data as SSE event"""
    lines = []
    if event:
        lines.append(f"event: {event}")
    lines.append(f"data: {safe_serialize(data)}")
    lines.append("")
    return "\n".join(lines) + "\n"

def create_sse_response(generator: AsyncGenerator) -> StreamingResponse:
    """Create SSE StreamingResponse from async generator"""
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

async def stream_progress(steps: list, callback) -> AsyncGenerator[str, None]:
    """Generic progress streaming helper"""
    total = len(steps)
    for i, step in enumerate(steps):
        progress = int((i + 1) / total * 100)
        result = await callback(step)
        yield sse_event({
            "step": step,
            "progress": progress,
            "result": result
        })
