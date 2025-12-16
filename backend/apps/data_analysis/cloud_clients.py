"""Cloud-agnostic abstraction for Data Analysis pipeline."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

from config import settings


class DataAnalysisNotConfigured(Exception):
    """Raised when cloud provider is not properly configured."""
    pass


@dataclass(frozen=True)
class QueryResult:
    """Result from SQL query execution."""
    query_id: str
    columns: list[str]
    rows: list[list[str]]


class DataAnalysisCloudClient(ABC):
    """Abstract base class for cloud-specific data analysis operations."""

    @property
    @abstractmethod
    def provider(self) -> str:
        """Return cloud provider name (aws, gcp, azure)."""
        pass

    @abstractmethod
    def put_json(self, uri: str, payload: dict[str, Any]) -> None:
        """Upload JSON to cloud storage."""
        pass

    @abstractmethod
    def put_bytes(self, uri: str, content: bytes) -> None:
        """Upload bytes to cloud storage."""
        pass

    @abstractmethod
    def start_pipeline(self, name: str, input_payload: dict[str, Any]) -> str:
        """Start ETL pipeline, return execution ID."""
        pass

    @abstractmethod
    def get_execution(self, execution_id: str) -> dict[str, Any]:
        """Get pipeline execution status."""
        pass

    @abstractmethod
    def get_execution_history(
        self,
        execution_id: str,
        next_token: Optional[str] = None,
        max_results: int = 200,
        reverse_order: bool = False,
    ) -> dict[str, Any]:
        """Get pipeline execution history/events."""
        pass

    @abstractmethod
    def run_sql_query(
        self,
        sql: str,
        database: str,
        timeout_seconds: float = 60.0,
        max_rows: int = 50,
    ) -> QueryResult:
        """Execute SQL query synchronously."""
        pass

    @abstractmethod
    async def run_sql_query_async(
        self,
        sql: str,
        database: str,
        timeout_seconds: float = 60.0,
        max_rows: int = 50,
    ) -> QueryResult:
        """Execute SQL query asynchronously."""
        pass

    @abstractmethod
    def get_table_schema(self, database: str, table: str) -> list[dict[str, str]]:
        """Get table schema (columns with names and types)."""
        pass

    def get_storage_uri(self, bucket: str, key: str) -> str:
        """Build storage URI for the cloud provider."""
        if self.provider == "aws":
            return f"s3://{bucket}/{key}"
        elif self.provider == "gcp":
            return f"gs://{bucket}/{key}"
        elif self.provider == "azure":
            return f"https://{bucket}.blob.core.windows.net/{key}"
        return f"s3://{bucket}/{key}"


def get_cloud_client() -> DataAnalysisCloudClient:
    """Factory function to get the appropriate cloud client based on config."""
    provider = getattr(settings, "CLOUD_PROVIDER", "aws").lower()

    if provider == "gcp":
        from apps.data_analysis.gcp_clients import GCPDataAnalysisClient
        return GCPDataAnalysisClient()
    elif provider == "azure":
        from apps.data_analysis.azure_clients import AzureDataAnalysisClient
        return AzureDataAnalysisClient()
    else:
        from apps.data_analysis.aws_client_wrapper import AWSDataAnalysisClient
        return AWSDataAnalysisClient()
