"""AWS implementation of DataAnalysisCloudClient - wraps existing aws_clients.py."""
from __future__ import annotations

from typing import Any, Optional

from apps.data_analysis.cloud_clients import DataAnalysisCloudClient, DataAnalysisNotConfigured, QueryResult
from apps.data_analysis.aws_clients import DataAnalysisAWSClients, DataAnalysisAWSNotConfigured


class AWSDataAnalysisClient(DataAnalysisCloudClient):
    """AWS implementation using existing DataAnalysisAWSClients."""

    def __init__(self):
        try:
            self._client = DataAnalysisAWSClients()
        except DataAnalysisAWSNotConfigured as e:
            raise DataAnalysisNotConfigured(str(e))

    @property
    def provider(self) -> str:
        return "aws"

    def put_json(self, uri: str, payload: dict[str, Any]) -> None:
        self._client.put_json_to_s3(uri, payload)

    def put_bytes(self, uri: str, content: bytes) -> None:
        self._client.put_bytes_to_s3(uri, content)

    def start_pipeline(self, name: str, input_payload: dict[str, Any]) -> str:
        return self._client.start_pipeline(name, input_payload)

    def get_execution(self, execution_id: str) -> dict[str, Any]:
        return self._client.get_execution(execution_id)

    def get_execution_history(
        self,
        execution_id: str,
        next_token: Optional[str] = None,
        max_results: int = 200,
        reverse_order: bool = False,
    ) -> dict[str, Any]:
        return self._client.get_execution_history(execution_id, next_token, max_results, reverse_order)

    def run_sql_query(
        self,
        sql: str,
        database: str,
        timeout_seconds: float = 60.0,
        max_rows: int = 50,
    ) -> QueryResult:
        result = self._client.run_athena_query(sql, database, timeout_seconds=timeout_seconds, max_rows=max_rows)
        return QueryResult(query_id=result.query_execution_id, columns=result.columns, rows=result.rows)

    async def run_sql_query_async(
        self,
        sql: str,
        database: str,
        timeout_seconds: float = 60.0,
        max_rows: int = 50,
    ) -> QueryResult:
        result = await self._client.run_athena_query_async(sql, database, timeout_seconds=timeout_seconds, max_rows=max_rows)
        return QueryResult(query_id=result.query_execution_id, columns=result.columns, rows=result.rows)

    def get_table_schema(self, database: str, table: str) -> list[dict[str, str]]:
        return self._client.get_table_schema(database, table)
