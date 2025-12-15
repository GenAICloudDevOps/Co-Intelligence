from apps.registry import registry, AppConfig
from apps.data_analysis.routes import router

registry.register(
    AppConfig(
        name="data-analysis",
        router=router,
        models_module="apps.data_analysis.models",
        display_name="Data Analysis",
        description="Agentic data analysis with AWS Step Functions + Glue + Athena",
        icon="📊",
        color="#14b8a6",
        status="active",
    )
)

