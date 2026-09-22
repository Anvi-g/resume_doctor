"""
Configuration settings for Resume Doctor Agentic (Azure AI-103).

Single source of truth for all environment configuration.
Services import ``settings`` from this module instead of calling ``os.getenv`` directly.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


_BASE_DIR = Path(__file__).resolve().parent.parent.parent  # project root


class Settings(BaseSettings):
    # --- Azure AI Foundry Agent Service (AI-103 Agents) ---
    # Foundry project endpoint: https://{ai-services-account-name}.services.ai.azure.com/api/projects/{project-name}
    AZURE_AI_PROJECT_ENDPOINT: Optional[str] = os.getenv("AZURE_AI_PROJECT_ENDPOINT", "")
    # Model deployment connected to the Foundry project (Models + endpoints tab).
    AZURE_AI_MODEL_DEPLOYMENT_NAME: Optional[str] = os.getenv(
        "AZURE_AI_MODEL_DEPLOYMENT_NAME",
        os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1-mini"),
    )
    # Name of the supervisor agent created in the Foundry project.
    AZURE_AGENT_NAME: str = "resume-doctor"
    # Set to "true"/"1" to force the deterministic offline orchestrator (unit tests, no cloud).
    FORCE_OFFLINE: bool = os.getenv("FORCE_OFFLINE", "false").lower() in ("true", "1")

    # --- Azure AI Document Intelligence (Member 1) ---
    AZURE_DOC_INTEL_ENDPOINT: Optional[str] = os.getenv("AZURE_DOC_INTEL_ENDPOINT", "")
    AZURE_DOC_INTEL_KEY: Optional[str] = os.getenv("AZURE_DOC_INTEL_KEY", "")

    # --- Azure AI Language (Member 2) ---
    AZURE_AI_LANG_ENDPOINT: Optional[str] = os.getenv("AZURE_AI_LANG_ENDPOINT", "")
    AZURE_AI_LANG_KEY: Optional[str] = os.getenv("AZURE_AI_LANG_KEY", "")

    # --- Azure OpenAI (Member 3; also used by the agent's model client when endpoint is set) ---
    AZURE_OPENAI_ENDPOINT: Optional[str] = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_KEY: Optional[str] = os.getenv("AZURE_OPENAI_KEY", "")
    AZURE_OPENAI_DEPLOYMENT_NAME: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1-mini")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2025-08-01-preview")

    # --- Entra service principal (Foundry + OpenAI), used by DefaultAzureCredential ---
    AZURE_TENANT_ID: Optional[str] = os.getenv("AZURE_TENANT_ID", "")
    AZURE_CLIENT_ID: Optional[str] = os.getenv("AZURE_CLIENT_ID", "")
    AZURE_CLIENT_SECRET: Optional[str] = os.getenv("AZURE_CLIENT_SECRET", "")

    # --- API Gateway ---
    PORT: int = os.getenv("PORT", 8000)
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")

    model_config = SettingsConfigDict(
        env_file=str(_BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# DefaultAzureCredential's EnvironmentCredential only reads real environment variables.
# Push the service-principal values loaded from .env into os.environ so the credential
# chain can authenticate against the Foundry project without requiring them to be exported
# in the shell. Only inject non-empty values; caller-supplied environment always wins.
for _sp_var in ("AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET"):
    _sp_value = getattr(settings, _sp_var)
    if _sp_value:
        os.environ.setdefault(_sp_var, _sp_value)