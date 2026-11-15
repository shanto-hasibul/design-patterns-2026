from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+psycopg://greenhouse:greenhouse@localhost:5432/greenhouse"
    )
    cors_origins: str = "http://localhost:5173"
    mqtt_broker_url: str | None = None
    mqtt_broker_port: int = 1883

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()