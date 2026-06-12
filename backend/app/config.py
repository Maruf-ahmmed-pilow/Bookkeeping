from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+psycopg2://bookkeeping:bookkeeping@localhost:5433/bookkeeping"
    )
    anthropic_api_key: str = ""
    ai_model: str = "claude-opus-4-8"
    confidence_threshold: float = 0.90
    log_level: str = "INFO"


settings = Settings()
