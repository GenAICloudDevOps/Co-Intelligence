from typing import AsyncGenerator, Dict, List
import google.generativeai as genai
from groq import Groq
import boto3
import json
from config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

MODEL_CONFIGS = {
    "gemini": {
        "models": ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-pro"],
        "default": "gemini-2.5-flash-lite"
    },
    "groq": {
        "models": ["groq/compound", "meta-llama/llama-4-scout-17b-16e-instruct"],
        "default": "groq/compound"
    },
    "bedrock": {
        "models": ["amazon.nova-lite-v1:0", "amazon.nova-pro-v1:0"],
        "default": "amazon.nova-lite-v1:0"
    }
}

DEFAULT_MODEL = "gemini-2.5-flash-lite"

class AIService:
    def __init__(self):
        self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
        self.bedrock = boto3.client('bedrock-runtime', region_name=settings.AWS_REGION)
    
    def get_available_models(self) -> Dict[str, List[str]]:
        """Return all available models grouped by provider"""
        return {
            "gemini": MODEL_CONFIGS["gemini"]["models"],
            "groq": MODEL_CONFIGS["groq"]["models"],
            "bedrock": MODEL_CONFIGS["bedrock"]["models"],
            "default": DEFAULT_MODEL
        }
    
    def _get_provider(self, model_name: str) -> str:
        """Determine provider from model name"""
        if model_name.startswith("gemini"):
            return "gemini"
        elif model_name.startswith("groq") or model_name.startswith("meta-llama"):
            return "groq"
        elif model_name.startswith("amazon"):
            return "bedrock"
        return "gemini"
    
    async def generate_response(self, prompt: str, model_name: str = DEFAULT_MODEL) -> str:
        """Generate a single response (non-streaming)"""
        provider = self._get_provider(model_name)
        
        if provider == "gemini":
            model = genai.GenerativeModel(model_name)
            response = await model.generate_content_async(prompt)
            return response.text
        elif provider == "groq":
            response = self.groq_client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                stream=False
            )
            return response.choices[0].message.content
        elif provider == "bedrock":
            response = self.bedrock.invoke_model(
                modelId=model_name,
                body=json.dumps({
                    "messages": [{"role": "user", "content": [{"text": prompt}]}],
                    "inferenceConfig": {"maxTokens": 1000, "temperature": 0.7}
                })
            )
            result = json.loads(response['body'].read())
            return result['output']['message']['content'][0]['text']
        raise ValueError(f"Unsupported provider: {provider}")
    
    async def call_model(self, model_name: str, prompt: str) -> str:
        """Non-streaming model call"""
        provider = self._get_provider(model_name)
        
        if provider == "gemini":
            return await self._call_gemini(model_name, prompt)
        elif provider == "groq":
            return await self._call_groq(model_name, prompt)
        elif provider == "bedrock":
            return await self._call_bedrock(model_name, prompt)
    
    async def stream_model(self, model_name: str, prompt: str, messages: list = None) -> AsyncGenerator[str, None]:
        """Streaming model call"""
        provider = self._get_provider(model_name)
        
        if provider == "gemini":
            async for chunk in self._stream_gemini(model_name, prompt):
                yield chunk
        elif provider == "groq":
            async for chunk in self._stream_groq(model_name, prompt, messages):
                yield chunk
        elif provider == "bedrock":
            async for chunk in self._stream_bedrock(model_name, prompt):
                yield chunk
    
    async def _call_gemini(self, model_name: str, prompt: str) -> str:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text
    
    async def _stream_gemini(self, model_name: str, prompt: str) -> AsyncGenerator[str, None]:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt, stream=True)
        for chunk in response:
            if chunk.text:
                yield chunk.text
    
    async def _call_groq(self, model_name: str, prompt: str) -> str:
        response = self.groq_client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    
    async def _stream_groq(self, model_name: str, prompt: str, messages: list = None) -> AsyncGenerator[str, None]:
        if messages is None:
            messages = [{"role": "user", "content": prompt}]
        
        response = self.groq_client.chat.completions.create(
            model=model_name,
            messages=messages,
            stream=True
        )
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def _call_bedrock(self, model_name: str, prompt: str) -> str:
        body = json.dumps({
            "messages": [{"role": "user", "content": [{"text": prompt}]}],
            "inferenceConfig": {"max_new_tokens": 512}
        })
        response = self.bedrock.invoke_model(modelId=model_name, body=body)
        result = json.loads(response['body'].read())
        return result['output']['message']['content'][0]['text']
    
    async def _stream_bedrock(self, model_name: str, prompt: str) -> AsyncGenerator[str, None]:
        # Bedrock streaming - for now, return as single chunk
        result = await self._call_bedrock(model_name, prompt)
        words = result.split()
        for word in words:
            yield word + " "

ai_service = AIService()
