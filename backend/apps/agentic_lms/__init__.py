from apps.registry import registry, AppConfig
from apps.agentic_lms.routes import router
from apps.agentic_lms.database import init_lms_db

registry.register(AppConfig(
    name="agentic-lms",
    router=router,
    models_module="apps.agentic_lms.models",
    init_function=init_lms_db,
    display_name="Agentic LMS",
    description="AI-powered learning management with course discovery and enrollment",
    description_lines=[
        "AI Course Discovery",
        "Natural Language Enrollment",
        "Progress Tracking",
        "LangGraph Agents",
    ],
    icon="🎓",
    color="#8b5cf6",
    status="active",
    requires_auth=True,
    show_in_ui=True,
))
