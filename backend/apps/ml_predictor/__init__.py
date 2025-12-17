from apps.registry import registry, AppConfig
from apps.ml_predictor.seed_datasets import seed_datasets
from apps.ml_predictor.routes import router

registry.register(AppConfig(
    name="ml-predictor",
    router=router,
    models_module="apps.ml_predictor.models",
    init_function=seed_datasets,
    display_name="ML Predictor",
    description="AI-powered multi-algorithm ML system with intelligent analysis",
    description_lines=[
        "Multi-Algorithm ML System",
        "Automatic Algorithm Selection",
        "Classification & Regression",
        "Comprehensive Metrics",
    ],
    icon="🤖",
    color="#8b5cf6",
    status="active",
    requires_auth=True,
    show_in_ui=True,
))
