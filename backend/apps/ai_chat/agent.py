from typing import TypedDict, AsyncGenerator
from langgraph.graph import StateGraph, START, END
import google.generativeai as genai
from groq import Groq
import boto3
import json
import re
from config import settings
from apps.ai_chat.utils import search_web, execute_code

genai.configure(api_key=settings.GEMINI_API_KEY)
groq_client = Groq(api_key=settings.GROQ_API_KEY)
bedrock = boto3.client('bedrock-runtime', region_name=settings.AWS_REGION)

class AgentState(TypedDict):
    messages: list
    model: str
    response: str

async def call_model(state: AgentState):
    messages = state["messages"]
    model = state.get("model", "gemini")
    
    last_message = messages[-1]["content"] if messages else ""
    
    if model == "gemini":
        gemini_model = genai.GenerativeModel(settings.GEMINI_MODEL)
        response = gemini_model.generate_content(last_message)
        result = response.text
    elif model == "groq":
        response = groq_client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[{"role": "user", "content": last_message}]
        )
        result = response.choices[0].message.content
    elif model == "bedrock":
        response = bedrock.invoke_model(
            modelId="amazon.nova-micro-v1:0",
            body='{"messages":[{"role":"user","content":[{"text":"' + last_message + '"}]}],"inferenceConfig":{"max_new_tokens":512}}'
        )
        result = json.loads(response['body'].read())['output']['message']['content'][0]['text']
    else:
        result = "Invalid model selected"
    
    return {"response": result}

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
    if model == "gemini" and code_execution_enabled:
        system_prompt = """You can execute Python code to help answer questions. When you need to calculate something or run code:
1. Write the code in a code block with ```python
2. I will execute it and show you the output
3. Use the output to formulate your final answer

Available Python functions: print, len, range, str, int, float, list, dict, set, tuple, sum, max, min, abs, round, sorted, enumerate, zip, map, filter, any, all"""
        
        full_messages.append({"role": "system", "content": system_prompt})
    
    full_messages.append({"role": "user", "content": last_message})
    
    if model == "gemini":
        gemini_model = genai.GenerativeModel(settings.GEMINI_MODEL)
        combined_prompt = "\n\n".join([m["content"] for m in full_messages])
        response = gemini_model.generate_content(combined_prompt, stream=True)
        
        full_response = ""
        for chunk in response:
            if chunk.text:
                full_response += chunk.text
                yield chunk.text
        
        # Check if response contains Python code and execute it
        if code_execution_enabled and "```python" in full_response:
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
                    
    elif model == "groq":
        response = groq_client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=full_messages,
            stream=True
        )
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    elif model == "bedrock":
        response = bedrock.invoke_model(
            modelId="amazon.nova-micro-v1:0",
            body='{"messages":[{"role":"user","content":[{"text":"' + last_message + '"}]}],"inferenceConfig":{"max_new_tokens":512}}'
        )
        result = json.loads(response['body'].read())['output']['message']['content'][0]['text']
        words = result.split()
        for word in words:
            yield word + " "

def create_chat_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("model", call_model)
    workflow.add_edge(START, "model")
    workflow.add_edge("model", END)
    return workflow.compile()

chat_graph = create_chat_graph()
