from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    supabase_url: str
    supabase_service_role_key: str
    supabase_jwt_secret: str
    database_url: str
    anthropic_api_key: str
    vapid_private_key: str
    vapid_public_key: str
    vapid_claims_email: str


settings = Settings()
