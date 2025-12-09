from datetime import datetime, timezone, timedelta
from collections import defaultdict, Counter
from fastapi import APIRouter, Depends, Query
from auth.utils import get_current_user
from apps.evaluations.models import EvaluationResult
from config import settings
from services.guardrails import redact_pii

router = APIRouter()


@router.get("/summary")
async def get_eval_summary(
    scope: str = Query("all", regex="^(all|me)$"),
    current_user=Depends(get_current_user),
):
    """Return aggregated evaluation metrics and extras (trend, issues, usage)."""
    now = datetime.now(timezone.utc)
    try:
        filters = {"app_name": "ai-chat"}
        if scope == "me":
            filters["user_id"] = current_user.id
        results = await EvaluationResult.filter(**filters).order_by("-created_at").limit(400)
    except Exception:
        return _empty_summary(now, scope)

    # Filter out rows with no signal
    results = [r for r in results if (r.context_precision + r.context_recall + r.response_relevancy + r.faithfulness) > 0]
    total = len(results)
    if total == 0:
        return _empty_summary(now, scope)

    def avg(attr: str) -> float:
        return sum(getattr(r, attr, 0) or 0 for r in results) / total

    def pick(attr_new: str, attr_old: str):
        val = avg(attr_new)
        if val == 0:
            return avg(attr_old)
        return val

    metrics = {
        "Context Precision": pick("context_precision", "grounding"),
        "Context Recall": pick("context_recall", "format_compliance"),
        "Response Relevancy": pick("response_relevancy", "helpfulness"),
        "Faithfulness": pick("faithfulness", "safety"),
    }

    metrics_map = {
        "context_precision": metrics["Context Precision"],
        "context_recall": metrics["Context Recall"],
        "response_relevancy": metrics["Response Relevancy"],
        "faithfulness": metrics["Faithfulness"],
    }

    # Deltas vs previous window
    previous = await EvaluationResult.filter(**filters).order_by("-created_at").offset(total).limit(total)

    def delta(attr):
        if not previous:
            return 0.0
        prev_total = len(previous)
        if prev_total == 0:
            return 0.0
        prev_avg = sum(getattr(r, attr, 0) or 0 for r in previous) / prev_total
        return metrics_map[attr] - prev_avg

    # Trend: average per day (last 7 days)
    trend_bucket: dict[str, dict[str, float]] = defaultdict(lambda: {"context_precision": [], "context_recall": [], "response_relevancy": [], "faithfulness": []})
    for r in results:
        day = r.created_at.date().isoformat()
        trend_bucket[day]["context_precision"].append(r.context_precision or r.grounding or 0)
        trend_bucket[day]["context_recall"].append(r.context_recall or r.format_compliance or 0)
        trend_bucket[day]["response_relevancy"].append(r.response_relevancy or r.helpfulness or 0)
        trend_bucket[day]["faithfulness"].append(r.faithfulness or r.safety or 0)
    trend = []
    for day in sorted(trend_bucket.keys(), reverse=True)[:7]:
        vals = trend_bucket[day]
        trend.append({
            "label": day,
            "context_precision": sum(vals["context_precision"]) / len(vals["context_precision"]),
            "context_recall": sum(vals["context_recall"]) / len(vals["context_recall"]),
            "response_relevancy": sum(vals["response_relevancy"]) / len(vals["response_relevancy"]),
            "faithfulness": sum(vals["faithfulness"]) / len(vals["faithfulness"]),
        })
    trend = list(reversed(trend))

    # Top issues: lowest combined faithfulness/relevancy
    issues_sorted = sorted(
        results,
        key=lambda r: min(
            r.faithfulness or r.safety or 0,
            r.response_relevancy or r.helpfulness or 0,
        )
    )
    issues = []
    for r in issues_sorted[:4]:
        score_f = r.faithfulness or r.safety or 0
        score_r = r.response_relevancy or r.helpfulness or 0
        reason = "Low faithfulness" if score_f <= score_r else "Low relevancy"
        sanitized_prompt, _, _ = redact_pii((r.prompt or "")[:160])
        sanitized_response, _, _ = redact_pii((r.response or "")[:160])
        issues.append({
            "prompt": sanitized_prompt,
            "response": sanitized_response,
            "faithfulness": score_f,
            "response_relevancy": score_r,
            "created_at": r.created_at.replace(tzinfo=timezone.utc).isoformat(),
            "reason": reason,
        })

    # Safety blocks proxy: count low faithfulness/relevancy in last 24h
    recent_cutoff = now - timedelta(hours=24)
    recent = [r for r in results if r.created_at.replace(tzinfo=timezone.utc) >= recent_cutoff]
    safety_blocks = len([r for r in recent if (r.faithfulness or 0) < 0.5 or (r.response_relevancy or 0) < 0.5])
    prev_window_cutoff = recent_cutoff - timedelta(hours=24)
    prev = [r for r in results if prev_window_cutoff <= r.created_at.replace(tzinfo=timezone.utc) < recent_cutoff]
    prev_blocks = len([r for r in prev if (r.faithfulness or 0) < 0.5 or (r.response_relevancy or 0) < 0.5])
    safety_change = safety_blocks - prev_blocks

    # Model usage
    model_counts = Counter([r.model_used for r in results if r.model_used])
    model_usage = [{"model": m, "count": c} for m, c in model_counts.most_common(5)]

    return {
        "run_id": "live-stream",
        "run_timestamp": results[0].created_at.replace(tzinfo=timezone.utc).isoformat(),
        "judge_model": settings.EVAL_JUDGE_MODEL,
        "metrics": [
            {"name": "Context Precision", "score": metrics["Context Precision"], "delta": delta("context_precision")},
            {"name": "Context Recall", "score": metrics["Context Recall"], "delta": delta("context_recall")},
            {"name": "Response Relevancy", "score": metrics["Response Relevancy"], "delta": delta("response_relevancy")},
            {"name": "Faithfulness", "score": metrics["Faithfulness"], "delta": delta("faithfulness")},
        ],
        "total_cases": total,
        "trend": trend,
        "issues": issues,
        "safety_blocks": {"count_24h": safety_blocks, "change": safety_change},
        "model_usage": model_usage,
        "scope": scope,
    }


def _empty_summary(now: datetime, scope: str):
    return {
        "run_id": "none",
        "run_timestamp": now.isoformat(),
        "judge_model": settings.EVAL_JUDGE_MODEL,
        "metrics": [
            {"name": "Context Precision", "score": 0.0, "delta": 0.0},
            {"name": "Context Recall", "score": 0.0, "delta": 0.0},
            {"name": "Response Relevancy", "score": 0.0, "delta": 0.0},
            {"name": "Faithfulness", "score": 0.0, "delta": 0.0},
        ],
        "total_cases": 0,
        "trend": [],
        "issues": [],
        "safety_blocks": {"count_24h": 0, "change": 0},
        "model_usage": [],
        "scope": scope,
    }
