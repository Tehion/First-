from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "crm@example.com"
    SMTP_USE_TLS: bool = True
    REMINDER_CHECK_INTERVAL_SECONDS: int = 60


settings = Settings()
