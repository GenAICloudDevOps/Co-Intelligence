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
    
    class Config:
        env_file = ".env"

settings = Settings()
