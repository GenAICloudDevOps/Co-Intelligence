"""Tortoise config for Aerich migrations."""
from config import settings
from services.database import _get_model_modules

TORTOISE_ORM = {
    "connections": {
        "default": settings.DATABASE_URL,
    },
    "apps": {
        "models": {
            "models": _get_model_modules() + ["aerich.models"],
            "default_connection": "default",
        }
    },
}
