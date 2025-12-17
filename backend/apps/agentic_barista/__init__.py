from apps.registry import registry, AppConfig
from apps.agentic_barista.routes import router
from apps.agentic_barista.seed_menu import seed_menu

registry.register(AppConfig(
    name="agentic-barista",
    router=router,
    models_module="apps.agentic_barista.models",
    init_function=seed_menu,
    display_name="Agentic Barista",
    description="LangGraph workflow with multi-agent coffee ordering system",
    description_lines=[
        "Natural Language Ordering",
        "Menu Discovery",
        "Smart Cart Management",
        "Order Confirmation",
    ],
    icon="☕",
    color="#f97316",
    status="active",
    requires_auth=False,
    show_in_ui=True,
))
