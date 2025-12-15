from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    
    GROQ_API_KEY: str
    
    TAVILY_API_KEY: str = ""
    
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    
    S3_BUCKET_NAME: str = ""
    CODE_EXECUTOR_URL: str = ""

    # AI settings
    AI_DEFAULT_MODEL: str = "gemini-2.5-flash"
    AI_FAST_MODEL: str = "gemini-2.5-flash"
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

    @property
    def cors_allowed_origins(self) -> list[str]:
        """Return parsed CORS origins list; empty means allow all."""
        if not self.CORS_ALLOW_ORIGINS:
            return []
        return [origin.strip() for origin in self.CORS_ALLOW_ORIGINS.split(",") if origin.strip()]

settings = Settings()
