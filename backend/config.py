from pydantic_settings import BaseSettings

from services.model_catalog import DEFAULT_MODEL_ID

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = DEFAULT_MODEL_ID
    
    GROQ_API_KEY: str
    
    TAVILY_API_KEY: str = ""
    
    # Cloud provider: aws | gcp | azure
    CLOUD_PROVIDER: str = "aws"
    
    # AWS settings
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_NAME: str = ""
    CODE_EXECUTOR_URL: str = ""
    
    # GCP settings (for Data Analysis)
    GCP_PROJECT_ID: str = ""
    GCP_WORKFLOWS_LOCATION: str = "us-central1"
    GCP_WORKFLOWS_NAME: str = ""
    GCP_BIGQUERY_DATASET: str = "co_intelligence_data_analysis"
    GCP_STORAGE_BUCKET: str = ""
    
    # Azure settings (for Data Analysis)
    AZURE_SUBSCRIPTION_ID: str = ""
    AZURE_RESOURCE_GROUP: str = ""
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_STORAGE_CONTAINER: str = "data-analysis"
    AZURE_LOGIC_APP_TRIGGER_URL: str = ""
    AZURE_SYNAPSE_SQL_ENDPOINT: str = ""
    AZURE_SYNAPSE_DATABASE: str = "co_intelligence"

    # AI settings
    AI_DEFAULT_MODEL: str = DEFAULT_MODEL_ID
    AI_FAST_MODEL: str = DEFAULT_MODEL_ID
    AI_QUALITY_MODEL: str = "gemini-1.5-pro"
    AI_ALT_MODEL: str = "groq/compound"
    AI_REQUEST_TIMEOUT: int = 60
    EVAL_JUDGE_MODEL: str = "groq/compound"

    # CORS / API surface
    CORS_ALLOW_ORIGINS: str | None = None
    AUTO_GENERATE_SCHEMAS: bool = True

    # Cookie settings for auth
    COOKIE_ACCESS_NAME: str = "access_token"
    COOKIE_REFRESH_NAME: str = "refresh_token"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    COOKIE_DOMAIN: str | None = None
    COOKIE_PATH: str = "/"

    # Frontend URL for auth emails
    FRONTEND_URL: str = ""

    # Password reset
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 60
    TEMP_PASSWORD_LENGTH: int = 12

    # Email (Gmail SMTP)
    GMAIL_SMTP_USER: str = ""
    GMAIL_SMTP_APP_PASSWORD: str = ""
    GMAIL_SMTP_FROM_NAME: str = "Co-Intelligence"

    # Data Analysis (App 8) - AWS pipeline resources
    DATA_ANALYSIS_STATE_MACHINE_ARN: str = ""
    DATA_ANALYSIS_GLUE_DATABASE: str = "co_intelligence_data_analysis"
    DATA_ANALYSIS_ATHENA_WORKGROUP: str = "co-intelligence-data-analysis"
    # Optional override; when blank we derive from S3_BUCKET_NAME
    DATA_ANALYSIS_ATHENA_OUTPUT_S3_URI: str = ""
    # Glue job names (kept for reference; Step Functions orchestrates these)
    DATA_ANALYSIS_GLUE_JOB_NAME_S3: str = "co-intelligence-data-analysis-etl-s3"
    DATA_ANALYSIS_GLUE_JOB_NAME_POSTGRES: str = "co-intelligence-data-analysis-etl-postgres"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def cors_allowed_origins(self) -> list[str]:
        """Return parsed CORS origins list; empty means allow all."""
        if not self.CORS_ALLOW_ORIGINS:
            return []
        return [origin.strip() for origin in self.CORS_ALLOW_ORIGINS.split(",") if origin.strip()]

settings = Settings()
