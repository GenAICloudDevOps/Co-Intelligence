"""
App package utilities.

We keep each app self-contained and registered via side effects in its
module. `load_apps` walks the apps directory and imports each app module
once so new apps can be added without touching `main.py`.
"""

import importlib
import pkgutil
from pathlib import Path

_EXCLUDE = {"registry", "__pycache__"}


def load_apps():
    """Dynamically import all app packages to trigger registration."""
    package_path = Path(__file__).parent
    for module_info in pkgutil.iter_modules([str(package_path)]):
        if module_info.name in _EXCLUDE:
            continue
        importlib.import_module(f"{__name__}.{module_info.name}")
