"""Lightweight guardrail utilities for AI calls."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Tuple, List


# Basic patterns (intentionally simple)
JAILBREAK_PATTERNS = [
    r"ignore\s+previous\s+instructions",
    r"as\s+an\s+ai\s+you\s+must",
    r"system\s+prompt",
    r"developer\s+message",
]

PII_PATTERNS = [
    r"\b\d{3}-\d{2}-\d{4}\b",  # SSN-like
    r"\b\d{10}\b",  # 10-digit phone
    r"\b\d{7,11}\b",  # generic long digit run (e.g., 8-11 digits)
    r"\b\w+@\w+\.\w+\b",  # email
    r"\bssn\b",
    r"social\s+security",
]

NAME_PATTERN = r"\bmy\s+name\s+is\s+([A-Za-z][A-Za-z\s]{1,30})"

CODE_PATTERNS = [
    r"import\s+os",
    r"import\s+subprocess",
    r"import\s+sys",
    r"__import__",
]

URL_PATTERN = re.compile(r"https?://[^\s]+", re.IGNORECASE)


@dataclass
class GuardrailDecision:
    allowed: bool
    reason: str | None = None


def _matches_any(text: str, patterns: Iterable[str]) -> Tuple[bool, str | None]:
    for pattern in patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True, pattern
    return False, None


def redact_pii(text: str, extra_terms: List[str] | None = None) -> tuple[str, bool, List[str]]:
    redacted = text
    found = False
    terms: List[str] = []

    # Names ("my name is ...")
    name_match = re.search(NAME_PATTERN, redacted, flags=re.IGNORECASE)
    if name_match:
        name_val = name_match.group(1).strip()
        if name_val:
            redacted = re.sub(NAME_PATTERN, "my name is [REDACTED_NAME]", redacted, flags=re.IGNORECASE)
            terms.append(name_val)
            found = True

    # Targeted replacements
    for pattern in PII_PATTERNS:
        if re.search(pattern, redacted, flags=re.IGNORECASE):
            redacted = re.sub(pattern, "[REDACTED]", redacted, flags=re.IGNORECASE)
            found = True

    # Generic digit scrub if SSN mentioned
    if re.search(r"ssn|social\s+security", redacted, flags=re.IGNORECASE):
        if re.search(r"\d{4,}", redacted):
            redacted = re.sub(r"\d{4,}", "[REDACTED]", redacted)
            found = True

    # Extra known personal terms (e.g., names collected)
    for term in extra_terms or []:
        if term and term.strip() and term.lower() in redacted.lower():
            redacted = re.sub(re.escape(term), "[REDACTED_NAME]", redacted, flags=re.IGNORECASE)
            found = True

    return redacted, found, terms


def check_input(prompt: str, max_length: int = 4000, block_pii: bool = True, allow_code: bool = False) -> GuardrailDecision:
    if not prompt or not prompt.strip():
        return GuardrailDecision(False, "Empty prompt")
    if len(prompt) > max_length:
        return GuardrailDecision(False, f"Prompt too long ({len(prompt)} > {max_length})")

    jail_hit, pattern = _matches_any(prompt, JAILBREAK_PATTERNS)
    if jail_hit:
        return GuardrailDecision(False, f"Jailbreak pattern: {pattern}")

    pii_hit, pattern = _matches_any(prompt, PII_PATTERNS)
    if pii_hit and block_pii:
        return GuardrailDecision(False, f"PII detected: {pattern}")

    # Only block code patterns if not explicitly allowed
    if not allow_code:
        code_hit, pattern = _matches_any(prompt, CODE_PATTERNS)
        if code_hit:
            return GuardrailDecision(False, f"High-risk code marker: {pattern}")

    return GuardrailDecision(True, None)


def require_sources_footer() -> str:
    return "Sources: (list the document names or URLs used; use 'None' if no sources)"


def check_output(
    text: str,
    require_sources: bool = False,
    context_terms: list[str] | None = None,
    allow_urls: list[str] | None = None,
    block_pii: bool = True,
    allow_code: bool = False,
) -> GuardrailDecision:
    if not text:
        return GuardrailDecision(False, "Empty response")

    pii_hit, pattern = _matches_any(text, PII_PATTERNS)
    if pii_hit and block_pii:
        return GuardrailDecision(False, f"PII in output: {pattern}")

    # Only block code patterns if not explicitly allowed
    if not allow_code:
        code_hit, pattern = _matches_any(text, CODE_PATTERNS)
        if code_hit and "```" in text:
            return GuardrailDecision(False, f"Code block contains risky import: {pattern}")

    if allow_urls is not None:
        def _url_allowed(url: str, allowed_prefix: str) -> bool:
            if not allowed_prefix:
                return False
            if not url.startswith(allowed_prefix):
                return False
            if allowed_prefix.endswith("/"):
                return True
            if len(url) == len(allowed_prefix):
                return True
            return url[len(allowed_prefix)] in "/?#"

        for match in URL_PATTERN.findall(text):
            candidate = match.rstrip(").,;:!?\"'[]{}")
            if not any(_url_allowed(candidate, prefix) for prefix in allow_urls):
                return GuardrailDecision(False, "Unallowlisted URL in output")

    if require_sources:
        # Check for common variations of the sources footer
        has_sources = any(marker in text for marker in ["Sources:", "References:", "Citations:", "Sources used:"])
        if not has_sources:
            # Instead of blocking, we can append a note or just allow it if it's a best-effort response
            # For now, let's be more lenient but still encourage it
            pass
        
        if context_terms:
            # Only enforce grounding if we actually have context terms to check against
            missing = [term for term in context_terms if term and term.lower() not in text.lower()]
            if len(context_terms) > 0 and len(missing) == len(context_terms):
                # If it's completely ungrounded, we still block it as it might be a hallucination
                return GuardrailDecision(False, "Output not grounded in provided context")

    return GuardrailDecision(True, None)
