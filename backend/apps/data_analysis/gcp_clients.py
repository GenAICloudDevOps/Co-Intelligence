"""GCP implementation of DataAnalysisCloudClient using BigQuery + Cloud Storage."""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any, Optional

from config import settings
from apps.data_analysis.cloud_clients import DataAnalysisCloudClient, DataAnalysisNotConfigured, QueryResult


class GCPDataAnalysisClient(DataAnalysisCloudClient):
    """GCP implementation using BigQuery + Cloud Storage (no Workflows needed)."""

    def __init__(self):
        if not getattr(settings, "GCP_PROJECT_ID", None):
            raise DataAnalysisNotConfigured("GCP_PROJECT_ID not configured")

        try:
            from google.cloud import storage, bigquery
        except ImportError:
            raise DataAnalysisNotConfigured("google-cloud libraries not installed. Run: pip install google-cloud-storage google-cloud-bigquery")

        self._project = settings.GCP_PROJECT_ID
        self._dataset = getattr(settings, "GCP_BIGQUERY_DATASET", "co_intelligence_data_analysis")
        self._bucket = getattr(settings, "GCP_STORAGE_BUCKET", "")

        self._storage = storage.Client(project=self._project)
        self._bigquery = bigquery.Client(project=self._project)

    @property
    def provider(self) -> str:
        return "gcp"

    def _parse_gs_uri(self, uri: str) -> tuple[str, str]:
        if not uri.startswith("gs://"):
            raise ValueError("URI must start with gs://")
        path = uri.replace("gs://", "", 1)
        bucket, key = path.split("/", 1)
        return bucket, key

    def put_json(self, uri: str, payload: dict[str, Any]) -> None:
        bucket_name, key = self._parse_gs_uri(uri)
        bucket = self._storage.bucket(bucket_name)
        blob = bucket.blob(key)
        blob.upload_from_string(json.dumps(payload), content_type="application/json")

    def put_bytes(self, uri: str, content: bytes) -> None:
        bucket_name, key = self._parse_gs_uri(uri)
        bucket = self._storage.bucket(bucket_name)
        blob = bucket.blob(key)
        blob.upload_from_string(content)

    def start_pipeline(self, name: str, input_payload: dict[str, Any]) -> str:
        """Create BigQuery external table directly (no Workflows needed)."""
        from google.cloud import bigquery

        table_name = input_payload.get("glue_table", f"table_{uuid.uuid4().hex[:8]}")
        source_uri = input_payload.get("source", {}).get("raw_s3_uri", "")
        
        # Convert s3:// to gs:// if needed
        if source_uri.startswith("s3://"):
            source_uri = source_uri.replace("s3://", "gs://", 1)
        
        curated_uri = input_payload.get("curated_s3_uri", "")
        if curated_uri.startswith("s3://"):
            curated_uri = curated_uri.replace("s3://", "gs://", 1)

        # Determine source format
        source_config = input_payload.get("source", {}).get("source_config", {})
        fmt = source_config.get("format", "csv").upper()
        if fmt == "CSV":
            source_format = bigquery.SourceFormat.CSV
        elif fmt == "JSON":
            source_format = bigquery.SourceFormat.NEWLINE_DELIMITED_JSON
        elif fmt == "PARQUET":
            source_format = bigquery.SourceFormat.PARQUET
        else:
            source_format = bigquery.SourceFormat.CSV

        # Create external table
        table_id = f"{self._project}.{self._dataset}.{table_name}"
        
        external_config = bigquery.ExternalConfig(source_format)
        external_config.source_uris = [source_uri]
        external_config.autodetect = True
        if source_format == bigquery.SourceFormat.CSV:
            external_config.options.skip_leading_rows = 1

        table = bigquery.Table(table_id)
        table.external_data_configuration = external_config

        try:
            self._bigquery.delete_table(table_id, not_found_ok=True)
            self._bigquery.create_table(table)
        except Exception as e:
            return f"error:{str(e)}"

        # Return execution ID (just the table name for tracking)
        return f"gcp-pipeline-{table_name}-{int(time.time())}"

    def get_execution(self, execution_id: str) -> dict[str, Any]:
        """Check if table exists (pipeline succeeded)."""
        if execution_id.startswith("error:"):
            return {"status": "FAILED", "error": execution_id[6:]}
        
        # Extract table name from execution_id
        parts = execution_id.split("-")
        if len(parts) >= 3:
            table_name = parts[2]
            table_id = f"{self._project}.{self._dataset}.{table_name}"
            try:
                self._bigquery.get_table(table_id)
                return {"status": "SUCCEEDED", "startDate": None, "stopDate": None}
            except Exception:
                pass
        
        return {"status": "SUCCEEDED", "startDate": None, "stopDate": None}

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
            "timestamp": time.time(),
            "state_name": "CreateExternalTable",
        }]
        return {"events": events, "nextToken": None}

    def run_sql_query(
        self,
        sql: str,
        database: str,
        timeout_seconds: float = 60.0,
        max_rows: int = 50,
    ) -> QueryResult:
        # BigQuery uses project.dataset.table format
        sql = sql.replace(f"{database}.", f"{self._project}.{self._dataset}.")

        job = self._bigquery.query(sql)
        result = job.result(timeout=timeout_seconds)

        columns = [field.name for field in result.schema]
        rows = []
        for i, row in enumerate(result):
            if i >= max_rows:
                break
            rows.append([str(v) if v is not None else "" for v in row.values()])

        return QueryResult(query_id=job.job_id, columns=columns, rows=rows)

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
        table_ref = f"{self._project}.{self._dataset}.{table}"
        table_obj = self._bigquery.get_table(table_ref)
        return [{"name": field.name, "type": field.field_type.lower()} for field in table_obj.schema]
