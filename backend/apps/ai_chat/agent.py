from typing import AsyncGenerator
from services.ai_service import ai_service, AIServiceError
from services.guardrails import require_sources_footer, redact_pii
from apps.ai_chat.utils import search_web, execute_code
import re

async def stream_model(
    messages: list,
    model: str,
    context_messages: list = None,
    document_context: str = None,
    web_search_enabled: bool = False,
    code_execution_enabled: bool = True,
    context_terms: list[str] | None = None,
    allow_urls: list[str] | None = None,
    grounded: bool = False,
) -> AsyncGenerator[str, None]:
    """Stream AI responses with document, web search, and code execution"""
    full_messages = []
    context_terms = context_terms or []
    allow_urls = allow_urls or []
    personal_terms: list[str] = []
    
    # Add document context if provided
    if document_context:
        full_messages.append({
            "role": "system",
            "content": f"You have access to the following document(s):\n\n{document_context}\n\nUse this information to answer questions."
        })
    
    # Add conversation context
    if context_messages:
        for msg in context_messages:
            full_messages.append({"role": msg["role"], "content": msg["content"]})
    
    last_message = messages[-1]["content"] if messages else ""
    
    # Perform web search if enabled
    search_context = ""
    if web_search_enabled and last_message:
        search_results = search_web(last_message)
        if search_results.get("results"):
            search_context = "\n\nWeb Search Results:\n"
            for i, result in enumerate(search_results["results"], 1):
                search_context += f"\n[{i}] {result['title']}\nURL: {result['url']}\n{result['content']}\n"
            last_message += search_context
    
    # Add code execution instruction for Gemini
    if model.startswith("gemini") and code_execution_enabled:
        system_prompt = """You can execute Python code to help answer questions. When you need to calculate something or run code:
1. Write the code in a code block with ```python
2. I will execute it and show you the output
3. Use the output to formulate your final answer

Available Python functions: print, len, range, str, int, float, list, dict, set, tuple, sum, max, min, abs, round, sorted, enumerate, zip, map, filter, any, all"""
        
        full_messages.append({"role": "system", "content": system_prompt})
    
    # Add grounding and source requirement only when context is present
    if grounded:
        grounding_footer = require_sources_footer()
        full_messages.append({"role": "system", "content": f"Answer only using provided context. If information is missing, respond with \"I don't know\". Include a short sources list.\n{grounding_footer}"})
    else:
        # Light safety/system guidance for general chat
        full_messages.append({"role": "system", "content": "Be concise, helpful, and avoid personal data. Do not execute code or include risky imports."})

    # Sanitize prior context messages to strip discovered personal terms
    sanitized_context = []
    for msg in context_messages or []:
        sanitized_content, _, extra_terms = redact_pii(msg["content"], extra_terms=personal_terms)
        if extra_terms:
            personal_terms.extend(extra_terms)
        sanitized_context.append({"role": msg["role"], "content": sanitized_content})
    context_messages = sanitized_context
    for msg in context_messages:
        full_messages.append(msg)

    # Redact PII in user message but continue the conversation
    redacted_message, had_pii, terms = redact_pii(last_message, extra_terms=personal_terms)
    if terms:
        personal_terms.extend(terms)

    if had_pii:
        full_messages.append({"role": "system", "content": "User personal details were removed. Do not request or repeat personal data."})
    full_messages.append({"role": "user", "content": redacted_message})
    
    # Use AIService for streaming
    combined_prompt = "\n\n".join([m["content"] for m in full_messages])
    
    full_response = ""
    chunks = []
    try:
        async for chunk in ai_service.stream_model(
            model,
            combined_prompt,
            full_messages,
            require_sources=grounded,
            context_terms=context_terms,
            allow_urls=allow_urls,
            block_pii=False,
        ):
            chunks.append(chunk)
            full_response += chunk
    except AIServiceError as exc:
        yield f"Response blocked: {exc}"
        return

    # Redact PII in output but keep the answer
    redacted_response, had_pii_out, _ = redact_pii(full_response, extra_terms=personal_terms)
    redaction_notice = ""
    if had_pii_out or personal_terms:
        redaction_notice = "Personal details were removed. I can't repeat names or IDs.\n\n"

    # If user asks for their identity or SSN, avoid answering directly
    if re.search(r"\bwhat\s+is\s+my\s+name\b", last_message, flags=re.IGNORECASE):
        redacted_response = "Personal details were removed, so I can't share your name. How else can I help?"
    elif re.search(r"\b(ssn|social\s+security)\b", last_message, flags=re.IGNORECASE):
        redacted_response = "I removed your SSN for safety and can't repeat it. I can still help with general guidance."
    else:
        if redaction_notice:
            redacted_response = redaction_notice + redacted_response

    # Yield sanitized response (single chunk for simplicity)
    yield redacted_response
    
    # Check if response contains Python code and execute it
    if code_execution_enabled and model.startswith("gemini") and "```python" in full_response:
        code_match = re.search(r'```python\n(.*?)\n```', full_response, re.DOTALL)
        if code_match:
            code = code_match.group(1)
            
            yield "\n\n🔄 *Executing code...*\n\n"
            
            # Execute the code
            result = execute_code(code)
            
            if result['success']:
                yield f"**Output:**\n```\n{result['output']}\n```\n\n"
            else:
                yield f"**Error:**\n```\n{result['errors']}\n```\n\n"
