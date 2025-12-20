from tortoise import fields
from models.base import BaseModel


class DataAnalysisDataset(BaseModel):
    user_id = fields.IntField(index=True)
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)

    source_type = fields.CharField(max_length=50)  # upload | s3 | postgres
    source_config = fields.JSONField(default=dict)  # {s3_uri,...} or {schema,table,query}

    raw_s3_uri = fields.CharField(max_length=2048, null=True)
    curated_s3_uri = fields.CharField(max_length=2048, null=True)

    glue_database = fields.CharField(max_length=255, null=True)
    glue_table = fields.CharField(max_length=255, null=True)

    status = fields.CharField(max_length=50, default="created")  # created | processing | ready | failed
    last_error = fields.TextField(null=True)
    last_run_id = fields.IntField(null=True)

    class Meta:
        table = "data_analysis_datasets"


class DataAnalysisRun(BaseModel):
    user_id = fields.IntField(index=True)
    dataset = fields.ForeignKeyField("models.DataAnalysisDataset", related_name="runs")

    run_type = fields.CharField(max_length=50, default="pipeline")  # pipeline | refresh
    status = fields.CharField(max_length=50, default="started")  # started | running | succeeded | failed

    transformation_spec = fields.JSONField(default=dict)
    spec_s3_uri = fields.CharField(max_length=2048, null=True)

    execution_arn = fields.CharField(max_length=2048, null=True)
    aws_region = fields.CharField(max_length=64, null=True)
    notification_sent = fields.BooleanField(default=False)

    class Meta:
        table = "data_analysis_runs"
