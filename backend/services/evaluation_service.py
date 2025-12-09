"""LLM-as-judge evaluation service."""
import json
from typing import Optional
from config import settings
from services.ai_service import ai_service, AIServiceError
from apps.evaluations.models import EvaluationResult

EVAL_PROMPT = """You are an evaluation judge.
Given:
- USER_PROMPT: {user_prompt}
- ASSISTANT_RESPONSE: {assistant_response}
- CONTEXT: {context}

Score the assistant on four axes from 0.0 to 1.0:
- context_precision: fraction of the answer supported by provided context; if no context is provided, set this to 1.0.
- context_recall: fraction of salient context used in the answer; if no context is provided, set this to 1.0.
- response_relevancy: how well the answer addresses the user prompt.
- faithfulness: factual consistency with the provided context; if no context is provided, judge factual consistency based on internal coherence and safety.

Respond with a JSON object only:
{{"context_precision": float, "context_recall": float, "response_relevancy": float, "faithfulness": float}}"""


async def evaluate_and_store(
    user_id: int,
    app_name: str,
    model_used: str,
    user_prompt: str,
    assistant_response: str,
    context: Optional[str] = None,
) -> Optional[EvaluationResult]:
    """Run a judge model and persist the scores."""
    context_snippet = (context or "")[:2000]
    prompt = EVAL_PROMPT.format(
        user_prompt=user_prompt[:2000],
        assistant_response=assistant_response[:4000],
        context=context_snippet,
    )

    try:
        raw = await ai_service.generate_response(
            prompt=prompt,
            model_name=settings.EVAL_JUDGE_MODEL,
            require_sources=False,
            block_pii=False,
        )
        data = json.loads(raw)
        context_precision = float(data.get("context_precision", 0))
        context_recall = float(data.get("context_recall", 0))
        response_relevancy = float(data.get("response_relevancy", 0))
        faithfulness = float(data.get("faithfulness", 0))
    except (AIServiceError, json.JSONDecodeError, ValueError, TypeError):
        # If judge fails, skip storing to avoid blocking main flow
        return None

    return await EvaluationResult.create(
        user_id=user_id,
        app_name=app_name,
        model_used=model_used,
        judge_model=settings.EVAL_JUDGE_MODEL,
        prompt=user_prompt[:2000],
        response=assistant_response[:4000],
        context=context_snippet,
        context_precision=context_precision,
        context_recall=context_recall,
        response_relevancy=response_relevancy,
        faithfulness=faithfulness,
        # Populate legacy fields for backward compatibility
        helpfulness=response_relevancy,
        grounding=context_precision,
        safety=faithfulness,
        format_compliance=context_recall,
    )
