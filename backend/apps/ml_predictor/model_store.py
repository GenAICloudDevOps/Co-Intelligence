import gzip
import io
import pickle
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from services.object_store import object_store, ObjectStoreNotConfigured, ObjectStoreError


@dataclass
class PersistedModel:
    model_name: str
    problem_type: str
    target_variable: str
    feature_names: list[str]
    label_encoders: Dict[str, Any]
    model: Any


def build_artifact_location(project_id: int, model_name: str) -> Tuple[str, str]:
    bucket = object_store.require_bucket()
    key = f"ml-models/{project_id}/{model_name}/model.pkl.gz"
    return bucket, key


def serialize_model_bundle(bundle: PersistedModel) -> bytes:
    raw = pickle.dumps(bundle, protocol=pickle.HIGHEST_PROTOCOL)
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
        gz.write(raw)
    return buf.getvalue()


def deserialize_model_bundle(data: bytes) -> PersistedModel:
    with gzip.GzipFile(fileobj=io.BytesIO(data), mode="rb") as gz:
        raw = gz.read()
    obj = pickle.loads(raw)
    if not isinstance(obj, PersistedModel):
        raise TypeError("Invalid model artifact payload")
    return obj


def upload_model_bundle(project_id: int, bundle: PersistedModel) -> Optional[Tuple[str, str]]:
    if not object_store.configured():
        return None
    try:
        bucket, key = build_artifact_location(project_id, bundle.model_name)
        object_store.put_bytes(bucket, key, serialize_model_bundle(bundle))
        return bucket, key
    except (ObjectStoreNotConfigured, ObjectStoreError):
        return None


def download_model_bundle(bucket: str, key: str) -> PersistedModel:
    data = object_store.get_bytes(bucket, key)
    return deserialize_model_bundle(data)
