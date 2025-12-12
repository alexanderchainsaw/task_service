from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    app_name: str = "Tasks Service"
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/postgres"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    worker_prefetch: int = 4
    queue_name: str = "tasks"
    queue_max_priority: int = 10
    api_prefix: str = "/api/v1"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="TASKS_")


settings = Settings()
