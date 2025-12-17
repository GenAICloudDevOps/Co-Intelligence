from apps.registry import registry, AppConfig
from apps.insurance_claims.routes import router

registry.register(AppConfig(
    name="insurance-claims",
    router=router,
    models_module="apps.insurance_claims.models",
    display_name="Insurance Claims",
    description="Role-based workflow for policy and claims management",
    description_lines=[
        "Role-Based Workflow",
        "Policy Management",
        "Claims Processing",
        "Status Tracking",
    ],
    icon="🚗",
    color="#06b6d4",
    status="active",
    requires_auth=True,
    show_in_ui=True,
))
