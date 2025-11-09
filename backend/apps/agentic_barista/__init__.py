from apps.registry import registry, AppConfig
from apps.agentic_barista.routes import router

registry.register(AppConfig(
    name="agentic-barista",
    router=router,
    models_module="apps.agentic_barista.models",
    display_name="Agentic Barista",
    description="LangGraph workflow with multi-agent coffee ordering system",
    icon="☕",
    color="#f97316",
    status="active"
))
