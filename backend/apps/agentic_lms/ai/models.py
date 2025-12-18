import os
import google.generativeai as genai
from langchain_aws import ChatBedrock

from services.model_catalog import DEFAULT_MODEL_ID

def get_model(model_name: str | None):
    """Get the appropriate LLM model based on name"""
    model_name = model_name or DEFAULT_MODEL_ID
    
    if model_name.startswith("gemini"):
        # Use direct Google Generative AI SDK
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        
        model_map = {
            "gemini-2.5-pro": "gemini-2.0-flash-exp",
            "gemini-2.5-flash": "gemini-2.0-flash-exp",
            "gemini-2.5-flash-lite": "gemini-2.0-flash-exp",
            "gemini-3-flash-preview": "gemini-3-flash-preview",
        }
        
        model_id = model_map.get(model_name, "gemini-2.0-flash-exp")
        return genai.GenerativeModel(model_id)
    
    elif model_name == "bedrock-nova":
        return ChatBedrock(
            model_id="amazon.nova-pro-v1:0",
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            credentials_profile_name=None
        )
    
    elif model_name == "bedrock-sonnet":
        return ChatBedrock(
            model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            credentials_profile_name=None
        )
    
    else:
        # Default to Gemini
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        return genai.GenerativeModel(DEFAULT_MODEL_ID)
