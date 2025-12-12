from apps.registry import registry, AppConfig
from apps.llms_fine_tuning.routes import router

registry.register(
    AppConfig(
        name="llms-fine-tuning",
        router=router,
        models_module="apps.llms_fine_tuning",
        init_function=None,
        display_name="LLMs Fine-Tuning",
        description="Run Tinker fine-tuning recipes and scripts",
        icon="🧪",
        color="#22c55e",
        status="active",
    )
)
