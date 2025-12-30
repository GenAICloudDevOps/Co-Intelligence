from apps.registry import registry, AppConfig
from apps.llms_fine_tuning.routes import router

registry.register(
    AppConfig(
        name="llms-fine-tuning",
        router=router,
        models_module="apps.llms_fine_tuning.models",
        init_function=None,
        display_name="LLMs Fine-Tuning",
        description="Run Tinker fine-tuning recipes and scripts",
        description_lines=[
            "Tinker API",
            "LoRA fine-tuning",
            "Scripted job runner",
            "Live logs + checkpoint sampling",
        ],
        icon="🧪",
        color="#22c55e",
        status="active",
        requires_auth=True,
        show_in_ui=True,
    )
)
