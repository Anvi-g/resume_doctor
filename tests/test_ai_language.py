"""
Unit Tests for Member 2 AI Language Service.
"""
from src.backend.services.ai_language import AILanguageService


def test_ai_language_redact():
    service = AILanguageService()
    result = service.redact_pii("John Doe john@example.com")
    assert result["status"] == "success"
    assert "redacted_text" in result
