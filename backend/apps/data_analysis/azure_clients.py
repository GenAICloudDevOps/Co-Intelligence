"""Azure implementation of DataAnalysisCloudClient using Logic Apps, Data Factory, Synapse."""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Optional

from config import settings
from apps.data_analysis.cloud_clients import DataAnalysisCloudClient, DataAnalysisNotConfigured, QueryResult


class AzureDataAnalysisClient(DataAnalysisCloudClient):
    """Azure implementation using Logic Apps + Data Factory + Synapse SQL."""

    def __init__(self):
        if not getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", None):
            raise DataAnalysisNotConfigured("AZURE_STORAGE_CONNECTION_STRING not configured")

        try:
            from azure.storage.blob import BlobServiceClient
            from azure.identity import DefaultAzureCredential
        except ImportError:
            raise DataAnalysisNotConfigured("azure libraries not installed. Run: pip install azure-storage-blob azure-identity")

        self._storage_conn = settings.AZURE_STORAGE_CONNECTION_STRING
        self._container = getattr(settings, "AZURE_STORAGE_CONTAINER", "data-analysis")
        self._resource_group = getattr(settings, "AZURE_RESOURCE_GROUP", "")
        self._subscription_id = getattr(settings, "AZURE_SUBSCRIPTION_ID", "")
        self._logic_app_url = getattr(settings, "AZURE_LOGIC_APP_TRIGGER_URL", "")
        self._synapse_endpoint = getattr(settings, "AZURE_SYNAPSE_SQL_ENDPOINT", "")
        self._synapse_database = getattr(settings, "AZURE_SYNAPSE_DATABASE", "co_intelligence")

        self._blob_service = BlobServiceClient.from_connection_string(self._storage_conn)
        self._credential = DefaultAzureCredential()

    @property
    def provider(self) -> str:
        return "azure"

    def _parse_blob_uri(self, uri: str) -> tuple[str, str]:
        # Handle both https://account.blob.../container/key and azure://container/key
        if uri.startswith("https://"):
            # https://account.blob.core.windows.net/container/key
            parts = uri.replace("https://", "").split("/", 2)
            container = parts[1] if len(parts) > 1 else self._container
            key = parts[2] if len(parts) > 2 else ""
            return container, key
        elif uri.startswith("azure://"):
            path = uri.replace("azure://", "", 1)
            container, key = path.split("/", 1)
            return container, key
        raise ValueError("URI must start with https:// or azure://")

    def put_json(self, uri: str, payload: dict[str, Any]) -> None:
        container, key = self._parse_blob_uri(uri)
        blob_client = self._blob_service.get_blob_client(container=container, blob=key)
        blob_client.upload_blob(json.dumps(payload), overwrite=True, content_type="application/json")

    def put_bytes(self, uri: str, content: bytes) -> None:
        container, key = self._parse_blob_uri(uri)
        blob_client = self._blob_service.get_blob_client(container=container, blob=key)
        blob_client.upload_blob(content, overwrite=True)

    def start_pipeline(self, name: str, input_payload: dict[str, Any]) -> str:
        if not self._logic_app_url:
            raise DataAnalysisNotConfigured("AZURE_LOGIC_APP_TRIGGER_URL not configured")

        import requests
        response = requests.post(
            self._logic_app_url,
            json={"name": name, **input_payload},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        return result.get("run_id") or result.get("id") or name

    def get_execution(self, execution_id: str) -> dict[str, Any]:
        # For Logic Apps, we'd need to query the run status
        # Simplified: return based on execution_id pattern or stored state
        if not self._resource_group or not self._subscription_id:
            return {"status": "UNKNOWN", "error": "Azure resource group not configured"}

        try:
            from azure.mgmt.logic import LogicManagementClient
            logic_client = LogicManagementClient(self._credential, self._subscription_id)

            # Parse logic app name and run id from execution_id
            # Format: logic_app_name/run_id
            parts = execution_id.split("/")
            if len(parts) >= 2:
                logic_app_name = parts[-2]
                run_id = parts[-1]
                run = logic_client.workflow_runs.get(self._resource_group, logic_app_name, run_id)
                status_map = {"Running": "RUNNING", "Succeeded": "SUCCEEDED", "Failed": "FAILED", "Cancelled": "CANCELLED"}
                return {
                    "status": status_map.get(run.status, "UNKNOWN"),
                    "startDate": run.start_time,
                    "stopDate": run.end_time,
                    "error": run.error.message if run.error else None,
                }
        except Exception as e:
            return {"status": "UNKNOWN", "error": str(e)}

        return {"status": "UNKNOWN"}

    def get_execution_history(
        self,
        execution_id: str,
        next_token: Optional[str] = None,
        max_results: int = 200,
        reverse_order: bool = False,
    ) -> dict[str, Any]:
        exec_info = self.get_execution(execution_id)
        events = [{
            "id": 1,
            "type": f"Execution{exec_info.get('status', 'Unknown').title()}",
            "timestamp": exec_info.get("startDate"),
            "state_name": "Pipeline",
        }]
        return {"events": events, "nextToken": None}

    def run_sql_query(
        self,
        sql: str,
        database: str,
        timeout_seconds: float = 60.0,
        max_rows: int = 50,
    ) -> QueryResult:
        if not self._synapse_endpoint:
            raise DataAnalysisNotConfigured("AZURE_SYNAPSE_SQL_ENDPOINT not configured")

        import pyodbc

        # Synapse SQL connection
        conn_str = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={self._synapse_endpoint};"
            f"DATABASE={self._synapse_database};"
            f"Authentication=ActiveDirectoryDefault;"
            f"Encrypt=yes;TrustServerCertificate=no;"
        )

        conn = pyodbc.connect(conn_str, timeout=int(timeout_seconds))
        cursor = conn.cursor()
        cursor.execute(sql)

        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = []
        for i, row in enumerate(cursor.fetchall()):
            if i >= max_rows:
                break
            rows.append([str(v) if v is not None else "" for v in row])

        cursor.close()
        conn.close()

        return QueryResult(query_id=f"synapse-{time.time()}", columns=columns, rows=rows)

    async def run_sql_query_async(
        self,
        sql: str,
        database: str,
        timeout_seconds: float = 60.0,
        max_rows: int = 50,
    ) -> QueryResult:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.run_sql_query(sql, database, timeout_seconds, max_rows)
        )

    def get_table_schema(self, database: str, table: str) -> list[dict[str, str]]:
        sql = f"""
        SELECT COLUMN_NAME, DATA_TYPE 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = '{table}'
        ORDER BY ORDINAL_POSITION
        """
        result = self.run_sql_query(sql, database, max_rows=100)
        return [{"name": row[0], "type": row[1]} for row in result.rows]
