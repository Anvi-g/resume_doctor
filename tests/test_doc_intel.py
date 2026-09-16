import pytest
from src.backend.services.doc_intelligence import DocIntelligenceService
from src.backend.orchestrator import MasterOrchestrator

def test_doc_intelligence_service_initialization():
    """Verify service initializes cleanly in fallback or live mode."""
    service = DocIntelligenceService()
    assert service is not None

def test_parse_resume_fallback_mode():
    """Verify resume parsing returns required schema fields."""
    service = DocIntelligenceService()
    dummy_pdf_bytes = b"%PDF-1.4 Sample Resume Text Content"
    
    result = service.parse_resume(dummy_pdf_bytes, filename="john_doe_resume.pdf")
    
    assert "raw_text" in result
    assert "page_count" in result
    assert "tables" in result
    assert "file_type" in result
    assert result["file_type"] == "pdf"
    assert len(result["raw_text"]) > 0

@pytest.mark.asyncio
async def test_master_orchestrator_pipeline_step1():
    """Verify MasterOrchestrator executes Step 1 successfully."""
    orchestrator = MasterOrchestrator()
    dummy_pdf_bytes = b"Sample text for orchestrator"
    
    response = await orchestrator.process_resume_pipeline(
        file_bytes=dummy_pdf_bytes,
        file_name="jane_doe_resume.pdf"
    )
    
    assert "parsed_document" in response
    assert response["pipeline_status"] == "Step 1 (Doc Intelligence) Ready"

