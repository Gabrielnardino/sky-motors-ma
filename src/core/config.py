from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    port: int = 8000
    log_level: str = "INFO"

    waha_url: str = "http://localhost:3000"
    waha_api_key: str = "skymotor2025"
    waha_session: str = "default"

    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "postgresql://postgres:password@localhost:5432/railway"

    vendor_phone: str = ""
    dealer_name: str = "Sky Motors"
    dealer_location: str = "Chelmsford, MA"
    dealer_timezone: str = "America/New_York"

    anthropic_api_key: str = ""
    groq_api_key: str = ""

    lang_smith_api_key: str = ""
    langchain_project: str = "sky-motors-ma"


settings = Settings()
