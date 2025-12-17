from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Query

from apps.registry import registry
from config import settings
from services.ai_service import ai_service

router = APIRouter()


def _aws_credentials_present() -> bool:
    env = os.environ
    return any(
        env.get(key)
        for key in (
            "AWS_ACCESS_KEY_ID",
            "AWS_PROFILE",
            "AWS_WEB_IDENTITY_TOKEN_FILE",
            "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
            "AWS_CONTAINER_CREDENTIALS_FULL_URI",
        )
    )


@router.get("/apps")
async def list_apps(include_hidden: bool = Query(False)) -> dict[str, Any]:
    apps_payload = []
    for app in registry.get_all():
        if not include_hidden and not getattr(app, "show_in_ui", True):
            continue
        apps_payload.append(
            {
                "id": app.name,
                "name": app.display_name,
                "description": getattr(app, "description_lines", []) or ([app.description] if app.description else []),
                "icon": app.icon,
                "color": app.color,
                "route": f"/apps/{app.name}",
                "status": app.status,
                "requiresAuth": getattr(app, "requires_auth", True),
            }
        )

    return {"apps": apps_payload, "cloudProvider": settings.CLOUD_PROVIDER}


@router.get("/models")
async def list_models() -> dict[str, Any]:
    providers_enabled = {
        "gemini": bool(getattr(settings, "GEMINI_API_KEY", "")),
        "groq": bool(getattr(settings, "GROQ_API_KEY", "")),
        "bedrock": bool(getattr(settings, "AWS_REGION", "")) and (_aws_credentials_present() or settings.CLOUD_PROVIDER == "aws"),
    }

    models = [
        {"id": "gemini-2.5-flash-lite", "name": "Gemini 2.5 Flash Lite", "provider": "Google", "enabled": providers_enabled["gemini"]},
        {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "provider": "Google", "enabled": providers_enabled["gemini"]},
        {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "provider": "Google", "enabled": providers_enabled["gemini"]},
        {"id": "groq/compound", "name": "Groq Compound", "provider": "Groq", "enabled": providers_enabled["groq"]},
        {
            "id": "meta-llama/llama-4-scout-17b-16e-instruct",
            "name": "Llama 4 Scout",
            "provider": "Groq",
            "enabled": providers_enabled["groq"],
        },
        {"id": "amazon.nova-lite-v1:0", "name": "Nova Lite", "provider": "AWS Bedrock", "enabled": providers_enabled["bedrock"]},
        {"id": "amazon.nova-pro-v1:0", "name": "Nova Pro", "provider": "AWS Bedrock", "enabled": providers_enabled["bedrock"]},
    ]

    routing = ai_service.get_available_models()
    default_model = getattr(settings, "AI_DEFAULT_MODEL", "") or getattr(settings, "GEMINI_MODEL", "") or "gemini-2.5-flash-lite"

    return {
        "defaultModel": default_model,
        "models": models,
        "tiers": routing.get("tiers", {}),
        "providers": routing.get("providers", {}),
        "cloudProvider": settings.CLOUD_PROVIDER,
    }
