from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Runtime
    app_name: str
    environment: str
    debug: bool

    # Logging
    log_level: str
    log_file: str

    # Database
    sqlite_db_path: str

    # Local LLM
    model_provider: str
    local_model: str
    ollama_url: str

    # Cloud
    cloud_provider: str
    monthly_budget_inr: int

    # Scheduler
    email_poll_interval_minutes: int
    expense_refresh_days: int

    class Config:
        env_file = ".env"


settings = Settings()