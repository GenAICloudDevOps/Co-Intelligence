from apps.registry import registry, AppConfig
from apps.insurance_claims.routes import router

registry.register(AppConfig(
    name="insurance-claims",
    router=router,
    models_module="apps.insurance_claims.models",
    display_name="Insurance Claims",
    description="Role-based workflow for policy and claims management",
    icon="🚗",
    color="#06b6d4",
    status="active"
))
