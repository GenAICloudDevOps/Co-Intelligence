from tortoise import fields
from models.base import BaseModel


class FineTuningRun(BaseModel):
    run_id = fields.CharField(max_length=64, unique=True)
    job_key = fields.CharField(max_length=100)
    status = fields.CharField(max_length=20, default="running")
    start_time = fields.DatetimeField()
    end_time = fields.DatetimeField(null=True)
    exit_code = fields.IntField(null=True)
    output = fields.JSONField(default=list)
    error = fields.TextField(null=True)

    class Meta:
        table = "llms_fine_tuning_runs"
