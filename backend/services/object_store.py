from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple
from urllib.parse import urlparse

import boto3

from config import settings


class ObjectStoreError(Exception):
    pass


class ObjectStoreNotConfigured(ObjectStoreError):
    pass


@dataclass(frozen=True)
class ObjectLocation:
    provider: str
    bucket: str
    key: str

    def uri(self) -> str:
        if self.provider == "aws":
            return f"s3://{self.bucket}/{self.key}"
        if self.provider == "gcp":
            return f"gs://{self.bucket}/{self.key}"
        if self.provider == "azure":
            return f"azure://{self.bucket}/{self.key}"
        return f"s3://{self.bucket}/{self.key}"


class ObjectStore:
    def provider(self) -> str:
        return getattr(settings, "CLOUD_PROVIDER", "aws").lower()

    def default_bucket(self) -> Optional[str]:
        provider = self.provider()
        if provider == "gcp":
            return getattr(settings, "GCP_STORAGE_BUCKET", "") or None
        if provider == "azure":
            return getattr(settings, "AZURE_STORAGE_CONTAINER", "") or None
        return getattr(settings, "S3_BUCKET_NAME", "") or None

    def build_uri(self, bucket: str, key: str, *, provider: Optional[str] = None) -> str:
        return ObjectLocation(provider=(provider or self.provider()), bucket=bucket, key=key).uri()

    def configured(self) -> bool:
        provider = self.provider()
        bucket = self.default_bucket()
        if not bucket:
            return False
        if provider == "azure" and not getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", ""):
            return False
        return True

    def require_bucket(self) -> str:
        bucket = self.default_bucket()
        if not bucket:
            provider = self.provider()
            if provider == "gcp":
                raise ObjectStoreNotConfigured("GCP_STORAGE_BUCKET not configured")
            if provider == "azure":
                raise ObjectStoreNotConfigured("AZURE_STORAGE_CONTAINER not configured")
            raise ObjectStoreNotConfigured("S3_BUCKET_NAME not configured")
        return bucket

    def put_bytes(self, bucket: str, key: str, content: bytes) -> str:
        provider = self.provider()
        if provider == "gcp":
            try:
                from google.cloud import storage
            except Exception as exc:  # pragma: no cover
                raise ObjectStoreError(f"GCP storage client unavailable: {exc}") from exc

            client = storage.Client()
            blob = client.bucket(bucket).blob(key)
            blob.upload_from_string(content)
            return self.build_uri(bucket, key, provider="gcp")

        if provider == "azure":
            if not getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", ""):
                raise ObjectStoreNotConfigured("AZURE_STORAGE_CONNECTION_STRING not configured")
            try:
                from azure.storage.blob import BlobServiceClient
            except Exception as exc:  # pragma: no cover
                raise ObjectStoreError(f"Azure blob client unavailable: {exc}") from exc

            svc = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
            container = svc.get_container_client(bucket)
            container.upload_blob(name=key, data=content, overwrite=True)
            return self.build_uri(bucket, key, provider="azure")

        # Default to AWS
        region = getattr(settings, "AWS_REGION", None) or None
        s3 = boto3.client("s3", region_name=region)
        s3.put_object(Bucket=bucket, Key=key, Body=content)
        return self.build_uri(bucket, key, provider="aws")

    def get_bytes(self, bucket: str, key: str) -> bytes:
        provider = self.provider()
        if provider == "gcp":
            try:
                from google.cloud import storage
            except Exception as exc:  # pragma: no cover
                raise ObjectStoreError(f"GCP storage client unavailable: {exc}") from exc

            client = storage.Client()
            blob = client.bucket(bucket).blob(key)
            return blob.download_as_bytes()

        if provider == "azure":
            if not getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", ""):
                raise ObjectStoreNotConfigured("AZURE_STORAGE_CONNECTION_STRING not configured")
            try:
                from azure.storage.blob import BlobServiceClient
            except Exception as exc:  # pragma: no cover
                raise ObjectStoreError(f"Azure blob client unavailable: {exc}") from exc

            svc = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
            blob = svc.get_blob_client(container=bucket, blob=key)
            return blob.download_blob().readall()

        region = getattr(settings, "AWS_REGION", None) or None
        s3 = boto3.client("s3", region_name=region)
        obj = s3.get_object(Bucket=bucket, Key=key)
        return obj["Body"].read()

    def parse_uri(self, uri: str) -> ObjectLocation:
        if uri.startswith("s3://"):
            rest = uri.replace("s3://", "", 1)
            bucket, key = rest.split("/", 1)
            return ObjectLocation(provider="aws", bucket=bucket, key=key)
        if uri.startswith("gs://"):
            rest = uri.replace("gs://", "", 1)
            bucket, key = rest.split("/", 1)
            return ObjectLocation(provider="gcp", bucket=bucket, key=key)
        if uri.startswith("azure://"):
            rest = uri.replace("azure://", "", 1)
            bucket, key = rest.split("/", 1)
            return ObjectLocation(provider="azure", bucket=bucket, key=key)

        parsed = urlparse(uri)
        if parsed.scheme in {"http", "https"} and parsed.hostname and parsed.hostname.endswith(".blob.core.windows.net"):
            # https://{account}.blob.core.windows.net/{container}/{blob}
            parts = parsed.path.lstrip("/").split("/", 1)
            if len(parts) != 2:
                raise ObjectStoreError("Invalid Azure blob URL")
            return ObjectLocation(provider="azure", bucket=parts[0], key=parts[1])

        raise ObjectStoreError("Unsupported storage URI")

    def get_bytes_from_uri(self, uri: str) -> bytes:
        loc = self.parse_uri(uri)
        provider = self.provider()
        if provider != loc.provider:
            # Cross-provider download isn't supported; keep data local to deployment provider.
            raise ObjectStoreError(f"Storage URI provider mismatch: {loc.provider} vs {provider}")
        return self.get_bytes(loc.bucket, loc.key)


object_store = ObjectStore()

