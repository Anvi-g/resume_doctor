"""
Alias/Wrapper module for Member 3 primary playbook path: `backend/app/services/openai_ats.py`.

This module re-exports `AzureOpenAIService` as `OpenAIATSService` to guarantee full 
backwards and forwards import compatibility across both project layout standards:
- `src.backend.services.azure_openai`
- `backend.app.services.openai_ats`
"""

# Import primary AzureOpenAIService from core services layer
from src.backend.services.azure_openai import AzureOpenAIService


class OpenAIATSService(AzureOpenAIService):
    """
    OpenAI ATS Service wrapper providing full class inheritance and compatibility 
    with backend/app/services/openai_ats.py as requested in Member 3 playbook.
    """
    pass


# Explicitly export OpenAIATSService and AzureOpenAIService classes
__all__ = ["OpenAIATSService", "AzureOpenAIService"]
