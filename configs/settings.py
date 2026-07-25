import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Explicitly load .env from the project root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(project_root, ".env")
load_dotenv(dotenv_path=env_path)


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
    gemini_api_key: str = None
    cerebras_api_key: str = None
    mistral_api_key: str = None

    # Scheduler
    email_poll_interval_minutes: int
    expense_refresh_days: int

    # Supabase / Consumer
    supabase_url: str
    supabase_key: str
    supabase_bucket: str = "jarvis-signals"
    supabase_insights_bucket: str = "jarvis-insights"
    supabase_db_url: str = None
    supabase_publishable_key: str = None
    supabase_secret_key: str = None
    consumer_poll_interval_minutes: int = 10

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()