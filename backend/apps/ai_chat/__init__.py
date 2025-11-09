from apps.registry import registry, AppConfig
from apps.ai_chat.routes import router

registry.register(AppConfig(
    name="ai-chat",
    router=router,
    models_module="apps.ai_chat.models",
    display_name="AI Chat",
    description="Multi-AI chat with document upload, web search, and code execution",
    icon="💬",
    color="#6366f1",
    status="active"
))
