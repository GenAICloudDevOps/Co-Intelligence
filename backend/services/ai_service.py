from typing import AsyncGenerator, Dict, List, Optional, Any, Tuple
import time
import json
import os
import asyncio
import functools
import google.generativeai as genai
from groq import Groq
import boto3
from config import settings
from core.logging import get_logger
from services.guardrails import check_input, check_output, require_sources_footer, GuardrailDecision

logger = get_logger("ai_service")

genai.configure(api_key=settings.GEMINI_API_KEY)

# Logical tiers -> concrete models (Gemini default)
MODEL_ROUTING: Dict[str, str] = {
    "default": settings.AI_DEFAULT_MODEL,
    "fast": settings.AI_FAST_MODEL,
    "quality": settings.AI_QUALITY_MODEL,
    "alt": settings.AI_ALT_MODEL,
}

PROVIDERS = {
    "gemini": {
        "prefixes": ("gemini",),
        "default": settings.AI_DEFAULT_MODEL,
        "timeout": settings.AI_REQUEST_TIMEOUT,
    },
    "groq": {
        "prefixes": ("groq", "meta-llama"),
        "default": "groq/compound",
        "timeout": settings.AI_REQUEST_TIMEOUT,
    },
    "bedrock": {
        "prefixes": ("amazon.",),
        "default": "amazon.nova-lite-v1:0",
        "timeout": settings.AI_REQUEST_TIMEOUT,
    },
}


class AIServiceError(Exception):
    pass


class AIService:
    def __init__(self):
        self.groq_client = Groq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None
        self.bedrock = (
            boto3.client('bedrock-runtime', region_name=settings.AWS_REGION)
            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY
            else None
        )
        self._cache: Dict[Tuple[str, str], Tuple[float, str]] = {}
        self._cache_ttl = 60  # seconds

    def resolve_model(self, model_or_tier: Optional[str]) -> str:
        """Resolve a logical tier (e.g. 'default') or model id to a concrete model id."""
        return self._resolve_model(model_or_tier)

    def get_available_models(self) -> Dict[str, List[str]]:
        """Return known logical tiers and provider defaults."""
        return {
            "tiers": MODEL_ROUTING,
            "providers": {name: cfg["default"] for name, cfg in PROVIDERS.items()},
        }

    def _resolve_model(self, model_or_tier: Optional[str]) -> str:
        if not model_or_tier:
            return MODEL_ROUTING.get("default", settings.AI_DEFAULT_MODEL)
        return MODEL_ROUTING.get(model_or_tier, model_or_tier)

    def _get_provider(self, model_name: str) -> str:
        for provider, cfg in PROVIDERS.items():
            if any(model_name.startswith(prefix) for prefix in cfg["prefixes"]):
                return provider
        return "gemini"

    def _cache_get(self, model: str, prompt: str) -> Optional[str]:
        key = (model, prompt)
        entry = self._cache.get(key)
        if not entry:
            return None
        ts, value = entry
        if time.time() - ts > self._cache_ttl:
            self._cache.pop(key, None)
            return None
        return value

    def _cache_set(self, model: str, prompt: str, value: str) -> None:
        self._cache[(model, prompt)] = (time.time(), value)

    async def generate_response(
        self,
        prompt: str,
        model_name: Optional[str] = None,
        require_sources: bool = False,
        context_terms: Optional[list[str]] = None,
        allow_urls: Optional[list[str]] = None,
        block_pii: bool = True,
    ) -> str:
        """Generate a single response (non-streaming) with routing, caching, and guardrails."""
        decision = check_input(prompt, block_pii=block_pii)
        if not decision.allowed:
            raise AIServiceError(f"Input blocked: {decision.reason}")

        resolved_model = self._resolve_model(model_name)
        cached = self._cache_get(resolved_model, prompt)
        if cached:
            return cached

        provider = self._get_provider(resolved_model)
        start = time.time()
        try:
            if provider == "gemini":
                text = await self._call_gemini(resolved_model, prompt)
            elif provider == "groq":
                text = await self._call_groq(resolved_model, prompt)
            elif provider == "bedrock":
                text = await self._call_bedrock(resolved_model, prompt)
            else:
                raise AIServiceError(f"Unsupported provider for model {resolved_model}")
        except Exception as exc:
            logger.error("ai_call_failed", extra={"model": resolved_model, "provider": provider, "error": str(exc)})
            raise AIServiceError(f"AI call failed: {exc}") from exc
        finally:
            duration = round((time.time() - start) * 1000, 2)
            logger.info("ai_call", extra={"model": resolved_model, "provider": provider, "duration_ms": duration})

        decision = check_output(
            text,
            require_sources=require_sources,
            context_terms=context_terms or [],
            allow_urls=allow_urls,
            block_pii=block_pii,
        )
        if not decision.allowed:
            reason = decision.reason or "Guardrail blocked the response"
            if reason == "Unallowlisted URL in output":
                raise AIServiceError(
                    "Output blocked: Response included a URL outside the allowed sources. "
                    "Try enabling web search or ask without requesting external links."
                )
            raise AIServiceError(f"Output blocked: {reason}")

        self._cache_set(resolved_model, prompt, text)
        return text

    async def call_model(self, model_name: str, prompt: str) -> str:
        """Compatibility wrapper: direct call without caching."""
        resolved_model = self._resolve_model(model_name)
        return await self.generate_response(prompt, resolved_model)

    async def stream_model(
        self,
        model_name: str,
        prompt: str,
        messages: list = None,
        require_sources: bool = False,
        context_terms: Optional[list[str]] = None,
        allow_urls: Optional[list[str]] = None,
        block_pii: bool = True,
    ) -> AsyncGenerator[str, None]:
        """Streaming model call with routing and guardrails (buffers before emit)."""
        decision = check_input(prompt, block_pii=block_pii)
        if not decision.allowed:
            raise AIServiceError(f"Input blocked: {decision.reason}")

        resolved_model = self._resolve_model(model_name)
        provider = self._get_provider(resolved_model)
        buffer: list[str] = []

        async def _yield_buffer():
            for chunk in buffer:
                yield chunk

        try:
            if provider == "gemini":
                async for chunk in self._stream_gemini(resolved_model, prompt):
                    buffer.append(chunk)
            elif provider == "groq":
                async for chunk in self._stream_groq(resolved_model, prompt, messages):
                    buffer.append(chunk)
            elif provider == "bedrock":
                async for chunk in self._stream_bedrock(resolved_model, prompt):
                    buffer.append(chunk)
            else:
                raise AIServiceError(f"Unsupported provider for model {resolved_model}")
        except Exception as exc:
            logger.error("ai_stream_failed", extra={"model": resolved_model, "provider": provider, "error": str(exc)})
            raise AIServiceError(f"AI stream failed: {exc}") from exc

        full_text = "".join(buffer)
        decision = check_output(
            full_text,
            require_sources=require_sources,
            context_terms=context_terms or [],
            allow_urls=allow_urls,
            block_pii=block_pii,
        )
        if not decision.allowed:
            logger.warning(
                "ai_stream_output_blocked",
                extra={
                    "model": resolved_model,
                    "reason": decision.reason,
                },
            )
            reason = decision.reason or "Guardrail blocked the response"
            if reason == "Unallowlisted URL in output":
                buffer = [
                    "I couldn't include a URL outside the allowed sources. "
                    "Try enabling web search or ask without requesting external links."
                ]
            else:
                buffer = [f"Response blocked: {reason}"]

        async for chunk in _yield_buffer():
            yield chunk

    async def _call_gemini(self, model_name: str, prompt: str) -> str:
        model = genai.GenerativeModel(model_name)
        response = await model.generate_content_async(prompt)
        return response.text

    async def _stream_gemini(self, model_name: str, prompt: str) -> AsyncGenerator[str, None]:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text

    async def _call_groq(self, model_name: str, prompt: str) -> str:
        if not self.groq_client:
            raise AIServiceError("Groq client not configured")
        response = self.groq_client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            timeout=settings.AI_REQUEST_TIMEOUT,
        )
        return response.choices[0].message.content

    async def _stream_groq(self, model_name: str, prompt: str, messages: list = None) -> AsyncGenerator[str, None]:
        if not self.groq_client:
            raise AIServiceError("Groq client not configured")
        if messages is None:
            messages = [{"role": "user", "content": prompt}]

        response = self.groq_client.chat.completions.create(
            model=model_name,
            messages=messages,
            stream=True,
            timeout=settings.AI_REQUEST_TIMEOUT,
        )
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def _call_bedrock(self, model_name: str, prompt: str) -> str:
        if not self.bedrock:
            raise AIServiceError("Bedrock client not configured")
        body = json.dumps({
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"max_new_tokens": 512, "temperature": 0.7},
        })
        response = self.bedrock.invoke_model(
            modelId=model_name,
            body=body,
        )
        result = json.loads(response['body'].read())
        return result['output']['message']['content'][0]['text']

    async def _stream_bedrock(self, model_name: str, prompt: str) -> AsyncGenerator[str, None]:
        # Bedrock streaming placeholder: yield split response
        result = await self._call_bedrock(model_name, prompt)
        for part in result.split():
            yield part + " "


ai_service = AIService()
