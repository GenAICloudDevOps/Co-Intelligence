from apps.registry import registry, AppConfig
from apps.ai_agent.routes import router

registry.register(
    AppConfig(
        name="ai-agent",
        router=router,
        models_module="apps.ai_agent.models",
        init_function=None,
        display_name="AI Agent",
        description="General Purpose AI Agent with code execution",
        description_lines=[
            "General Purpose AI",
            "Code Execution",
            "Build & Deploy",
            "Live URL Serving",
        ],
        icon="🦾",
        color="#ec4899",
        status="active",
        requires_auth=True,
        show_in_ui=True,
    )
)
