import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    AZURE_DOC_INTEL_ENDPOINT: Optional[str] = ""
    AZURE_DOC_INTEL_KEY: Optional[str] = ""
    AZURE_AI_LANG_ENDPOINT: Optional[str] = ""
    AZURE_AI_LANG_KEY: Optional[str] = ""
    AZURE_OPENAI_ENDPOINT: Optional[str] = ""
    AZURE_OPENAI_KEY: Optional[str] = ""
    AZURE_OPENAI_DEPLOYMENT_NAME: str = "gpt-4o"
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"
    PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
