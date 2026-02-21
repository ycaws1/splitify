from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, AliasChoices

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    supabase_url: str
    supabase_service_role_key: str
    supabase_jwt_secret: str = ""
    database_url: str
    direct_database_url: str = ""
    llm_api_key: str = Field(validation_alias=AliasChoices('llm_api_key', 'google_api_key', 'gemini_api_key'))
    vapid_private_key: str
    vapid_public_key: str
    vapid_claims_email: str
    llm_model_name: str = Field(default="gemini/gemini-2.5-flash-lite", validation_alias=AliasChoices('llm_model_name', 'google_model_name'))
    cors_origins: str = "http://localhost:3000"


settings = Settings()

# Trigger reload for .env update
