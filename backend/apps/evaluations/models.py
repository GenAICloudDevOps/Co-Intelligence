from tortoise import fields
from models.base import BaseModel


class EvaluationResult(BaseModel):
    user_id = fields.IntField()
    app_name = fields.CharField(max_length=100)
    model_used = fields.CharField(max_length=200)
    judge_model = fields.CharField(max_length=200)
    prompt = fields.TextField()
    response = fields.TextField()
    context = fields.TextField(null=True)
    # Legacy metrics
    helpfulness = fields.FloatField(default=0)
    grounding = fields.FloatField(default=0)
    safety = fields.FloatField(default=0)
    format_compliance = fields.FloatField(default=0)
    # New metrics
    context_precision = fields.FloatField(default=0)
    context_recall = fields.FloatField(default=0)
    response_relevancy = fields.FloatField(default=0)
    faithfulness = fields.FloatField(default=0)

    class Meta:
        table = "evaluation_results"
