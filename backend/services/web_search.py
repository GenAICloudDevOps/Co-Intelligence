from __future__ import annotations

from typing import Any

from config import settings


def search_web(query: str, max_results: int = 3) -> dict[str, Any]:
    """Search the web using Tavily (best-effort)."""
    api_key = getattr(settings, "TAVILY_API_KEY", "") or ""
    if not api_key:
        return {"results": [], "error": "Tavily API key not configured. Please set TAVILY_API_KEY in your .env file.", "query": query}

    try:
        from tavily import TavilyClient
    except Exception as exc:  # pragma: no cover
        return {"results": [], "error": f"Tavily client unavailable: {exc}", "query": query}

    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(query, max_results=max_results) or {}
        return {
            "results": [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", ""),
                }
                for r in response.get("results", [])
            ],
            "query": query,
        }
    except Exception as exc:
        return {"results": [], "error": str(exc), "query": query}

