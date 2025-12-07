from tortoise import fields
from models.base import BaseModel

class Dataset(BaseModel):
    user_id = fields.IntField()
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    file_path = fields.CharField(max_length=500, null=True)
    rows = fields.IntField(default=0)
    columns = fields.IntField(default=0)
    column_names = fields.JSONField(default=list)
    data_types = fields.JSONField(default=dict)
    is_sample = fields.BooleanField(default=False)
    
    class Meta:
        table = "ml_datasets"

class MLProject(BaseModel):
    user_id = fields.IntField()
    dataset_id = fields.IntField()
    name = fields.CharField(max_length=255)
    problem_description = fields.TextField()
    problem_type = fields.CharField(max_length=50)  # "classification" or "regression"
    target_variable = fields.CharField(max_length=255)
    status = fields.CharField(max_length=50, default="pending")  # pending, processing, completed, failed
    error_message = fields.TextField(null=True)
    
    class Meta:
        table = "ml_projects"

class ModelResult(BaseModel):
    project_id = fields.IntField()
    algorithm_name = fields.CharField(max_length=100)
    algorithm_display_name = fields.CharField(max_length=100)
    metrics = fields.JSONField()  # accuracy, precision, recall, f1, rmse, mae, r2, etc.
    predictions = fields.JSONField()  # list of predictions
    feature_importance = fields.JSONField(null=True)  # dict of feature importance
    training_time = fields.FloatField(default=0.0)
    
    class Meta:
        table = "ml_model_results"

class TrainingRun(BaseModel):
    project_id = fields.IntField()
    algorithms_used = fields.JSONField()  # list of algorithm names
    best_model = fields.CharField(max_length=100)
    best_metrics = fields.JSONField()
    comparison_report = fields.JSONField()  # detailed comparison
    
    class Meta:
        table = "ml_training_runs"
