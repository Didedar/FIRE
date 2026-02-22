from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://fire_user:fire_password@localhost:5433/fire_db"
    NLP_SERVICE_URL: str = "http://nlp-service:8001/analyze"
    CSV_STORAGE_PATH: str = "csv_storage"
    GROQ_API_KEY: str | None = None
    BATCH_SEMAPHORE_LIMIT: int = 10

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
