from fastapi import APIRouter
from apps.registry import AppConfig, registry
from .routes import router

config = AppConfig(
    name="evaluations",
    router=router,
    models_module="apps.evaluations.models",
    display_name="Evaluations",
    description="LLM-as-judge evaluation summaries",
    icon="📊",
    color="#22c55e",
    requires_auth=True,
    show_in_ui=False,
)

registry.register(config)
