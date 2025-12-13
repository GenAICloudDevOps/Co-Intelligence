import gzip
import io
import pickle
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import boto3

from config import settings


@dataclass
class PersistedModel:
    model_name: str
    problem_type: str
    target_variable: str
    feature_names: list[str]
    label_encoders: Dict[str, Any]
    model: Any


def _s3_client():
    if not settings.AWS_ACCESS_KEY_ID or not settings.S3_BUCKET_NAME:
        return None
    return boto3.client("s3", region_name=settings.AWS_REGION)


def build_artifact_location(project_id: int, model_name: str) -> Tuple[str, str]:
    if not settings.S3_BUCKET_NAME:
        raise RuntimeError("S3_BUCKET_NAME not configured")
    key = f"ml-models/{project_id}/{model_name}/model.pkl.gz"
    return settings.S3_BUCKET_NAME, key


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
    client = _s3_client()
    if client is None:
        return None
    bucket, key = build_artifact_location(project_id, bundle.model_name)
    client.put_object(Bucket=bucket, Key=key, Body=serialize_model_bundle(bundle))
    return bucket, key


def download_model_bundle(bucket: str, key: str) -> PersistedModel:
    client = _s3_client()
    if client is None:
        raise RuntimeError("S3 client not configured")
    obj = client.get_object(Bucket=bucket, Key=key)
    body = obj["Body"].read()
    return deserialize_model_bundle(body)

