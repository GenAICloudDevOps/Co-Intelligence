from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ProviderKey = Literal["gemini", "groq", "bedrock"]


@dataclass(frozen=True)
class ModelSpec:
    id: str
    name: str
    provider: str
    provider_key: ProviderKey


# Single source of truth for the default model used across the product.
DEFAULT_MODEL_ID = "gemini-3-flash-preview"


MODEL_CATALOG: list[ModelSpec] = [
    ModelSpec(id="gemini-3-flash-preview", name="Gemini 3 Flash", provider="Google", provider_key="gemini"),
    ModelSpec(id="gemini-2.5-flash-lite", name="Gemini 2.5 Flash Lite", provider="Google", provider_key="gemini"),
    ModelSpec(id="gemini-2.5-flash", name="Gemini 2.5 Flash", provider="Google", provider_key="gemini"),
    ModelSpec(id="gemini-2.5-pro", name="Gemini 2.5 Pro", provider="Google", provider_key="gemini"),
    ModelSpec(id="groq/compound", name="Groq Compound", provider="Groq", provider_key="groq"),
    ModelSpec(
        id="meta-llama/llama-4-scout-17b-16e-instruct",
        name="Llama 4 Scout",
        provider="Groq",
        provider_key="groq",
    ),
    ModelSpec(id="amazon.nova-lite-v1:0", name="Nova Lite", provider="AWS Bedrock", provider_key="bedrock"),
    ModelSpec(id="amazon.nova-pro-v1:0", name="Nova Pro", provider="AWS Bedrock", provider_key="bedrock"),
]


def to_meta_models(*, providers_enabled: dict[ProviderKey, bool]) -> list[dict[str, Any]]:
    """Return the model catalog in a shape suitable for /api/meta/models."""
    return [
        {
            "id": spec.id,
            "name": spec.name,
            "provider": spec.provider,
            "enabled": bool(providers_enabled.get(spec.provider_key, False)),
        }
        for spec in MODEL_CATALOG
    ]

