from typing import AsyncGenerator
from services.ai_service import ai_service
from apps.ai_chat.utils import search_web, execute_code
import re

async def stream_model(messages: list, model: str, context_messages: list = None, document_context: str = None, web_search_enabled: bool = False, code_execution_enabled: bool = True) -> AsyncGenerator[str, None]:
    """Stream AI responses with document, web search, and code execution"""
    full_messages = []
    
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
    
    full_messages.append({"role": "user", "content": last_message})
    
    # Use AIService for streaming
    combined_prompt = "\n\n".join([m["content"] for m in full_messages])
    
    full_response = ""
    async for chunk in ai_service.stream_model(model, combined_prompt, full_messages):
        full_response += chunk
        yield chunk
    
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

