from apps.registry import registry, AppConfig
from apps.agentic_tutor.routes import router

registry.register(AppConfig(
    name="agentic-tutor",
    router=router,
    models_module="apps.agentic_tutor.models",
    display_name="Agentic Tutor",
    description="AI-powered interactive learning with multi-agent tutoring system",
    icon="👨‍🏫",
    color="#f59e0b",
    status="active"
))
