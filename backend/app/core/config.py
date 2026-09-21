from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")

    APP_ENV: str = "development"
    PAYMENT_PROVIDER: str = "manual"

    # Supabase
    SUPABASE_URL: str
    SUPABASE_PUBLISHABLE_KEY: str
    SUPABASE_SECRET_KEY: str

    GREENAPI_INSTANCE_ID: str
    GREENAPI_TOKEN_ID: str

    EMAIL_PROVIDER: str = "resend"
    EMAIL_API_KEY: str
    EMAIL_FROM_ADDRESS: str

    API_BASE_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:8000"


settings = Settings()