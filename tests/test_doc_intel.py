"""
Unit Tests for Member 1 Document Intelligence Service.
"""
from src.backend.services.doc_intelligence import DocIntelligenceService


def test_doc_intelligence_parse():
    service = DocIntelligenceService()
    result = service.parse_resume(b"Jane Doe\nSoftware Engineer", "resume.pdf")
    assert result["status"] == "success"
    assert "extracted_text" in result
