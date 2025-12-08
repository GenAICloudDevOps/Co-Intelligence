"""In-memory cache for trained models keyed by project."""
import os
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class CachedModel:
    project_id: int
    model_name: str
    model: Any
    feature_names: List[str]
    target_variable: Optional[str]
    dataset_path: str
    dataset_mtime: float


class ModelCache:
    """Thread-safe in-memory cache for trained models."""

    def __init__(self):
        self._cache: Dict[int, CachedModel] = {}
        self._lock = threading.Lock()

    def get(self, project_id: int, model_name: str, dataset_path: str) -> Optional[CachedModel]:
        mtime = self._get_mtime(dataset_path)
        with self._lock:
            cached = self._cache.get(project_id)
            if not cached:
                return None
            if cached.model_name != model_name:
                return None
            if cached.dataset_path != dataset_path:
                return None
            if cached.dataset_mtime != mtime:
                return None
            return cached

    def set(self, entry: CachedModel) -> None:
        with self._lock:
            self._cache[entry.project_id] = entry

    def _get_mtime(self, path: str) -> float:
        try:
            return os.path.getmtime(path)
        except OSError:
            return 0.0


model_cache = ModelCache()
