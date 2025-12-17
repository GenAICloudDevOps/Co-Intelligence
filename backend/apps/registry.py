"""
App Registry - Auto-discover and register apps
"""
from typing import List, Dict, Callable, Optional
from fastapi import APIRouter

class AppConfig:
    def __init__(
        self,
        name: str,
        router: APIRouter,
        models_module: str,
        init_function: Optional[Callable] = None,
        display_name: str = "",
        description: str = "",
        description_lines: Optional[List[str]] = None,
        icon: str = "🤖",
        color: str = "#6366f1",
        status: str = "active",
        requires_auth: bool = True,
        show_in_ui: bool = True,
    ):
        self.name = name
        self.router = router
        self.models_module = models_module
        self.init_function = init_function
        self.display_name = display_name or name.replace("-", " ").title()
        self.description = description
        self.description_lines = description_lines or ([description] if description else [])
        self.icon = icon
        self.color = color
        self.status = status
        self.requires_auth = requires_auth
        self.show_in_ui = show_in_ui

class AppRegistry:
    def __init__(self):
        self._apps: Dict[str, AppConfig] = {}
    
    def register(self, app: AppConfig):
        self._apps[app.name] = app
    
    def get_all(self) -> List[AppConfig]:
        return list(self._apps.values())
    
    def get_routers(self) -> List[tuple]:
        return [(app.router, f"/api/apps/{app.name}", [app.name]) for app in self._apps.values()]
    
    def get_model_modules(self) -> List[str]:
        return [app.models_module for app in self._apps.values()]
    
    async def initialize_apps(self):
        for app in self._apps.values():
            if app.init_function:
                await app.init_function()

registry = AppRegistry()
