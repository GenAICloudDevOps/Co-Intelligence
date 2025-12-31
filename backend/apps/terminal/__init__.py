from apps.registry import registry, AppConfig
from apps.terminal.routes import router

registry.register(
    AppConfig(
        name="terminal",
        router=router,
        models_module="apps.terminal.models",
        init_function=None,
        display_name="Terminal",
        description="Isolated Ubuntu terminal sessions",
        description_lines=[
            "Ubuntu 22.04 shell",
            "Full internet access",
            "Isolated container per session",
            "No access to other apps",
        ],
        icon="🖥️",
        color="#0ea5e9",
        status="active",
        requires_auth=True,
        show_in_ui=True,
    )
)
