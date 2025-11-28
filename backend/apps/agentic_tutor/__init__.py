from apps.registry import registry, AppConfig
from apps.agentic_tutor.routes import router
from apps.agentic_tutor.seed_topics import seed_topics

registry.register(AppConfig(
    name="agentic-tutor",
    router=router,
    models_module="apps.agentic_tutor.models",
    init_function=seed_topics,
    display_name="Agentic Tutor",
    description="AI-powered interactive learning with multi-agent tutoring system",
    icon="👨🏫",
    color="#f59e0b",
    status="active"
))
