import pytest
import json
import os
from src.backend.services.doc_intelligence import DocIntelligenceService
from src.backend.orchestrator import MasterOrchestrator

def test_doc_intelligence_service_initialization():
    service = DocIntelligenceService()
    assert service is not None
    print(f"\n[Test 1 Output] Mode: {'Live Azure' if service.is_live else 'Local Fallback'}")

def test_parse_resume_section_extraction():
    """Verify Section header parsing in Day 2."""
    service = DocIntelligenceService()
    sample_text = (
        "Jane Doe\nEmail: jane@example.com\n\n"
        "EXPERIENCE\nSenior Developer at ACME Corp\n\n"
        "SKILLS\nPython, Azure, Docker, FastAPI\n\n"
        "EDUCATION\nB.S. Computer Science"
    ).encode("utf-8")

    result = service.parse_resume(sample_text, filename="sample.pdf")
    
    print("\n=== [Test 2 Output] Section Extraction ===")
    print(json.dumps(result.get("sections"), indent=2))
    
    assert "sections" in result
    assert "EXPERIENCE" in result["sections"]
    assert "SKILLS" in result["sections"]

@pytest.mark.asyncio
async def test_master_orchestrator_day2_pipeline():
    """Verify Day 2 MasterOrchestrator response contract."""
    orchestrator = MasterOrchestrator()
    dummy_bytes = b"Sample resume content for pipeline test"
    
    response = await orchestrator.process_resume_pipeline(dummy_bytes, "test_resume.pdf")
    
    print("\n=== [Test 3 Output] Day 2 MasterOrchestrator Pipeline ===")
    print(json.dumps(response, indent=2))
    
    assert response["pipeline_stages"]["stage_1_doc_intel"] is True
    assert "document_metadata" in response
    assert "parsed_content" in response

def test_parse_actual_cv_anvi_pdf():
    """Verify parsing real file cv_anvi.pdf with complete JSON output."""
    service = DocIntelligenceService()
    pdf_path = os.path.join("tests", "sample_resumes", "cv_anvi.pdf")
    
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
            
        result = service.parse_resume(pdf_bytes, filename="cv_anvi.pdf")
        
        print("\n=== [Test 4 Output] Complete Parsed Document JSON (cv_anvi.pdf) ===")
        print(json.dumps(result, indent=2))
        
        assert len(result["raw_text"]) > 0
        assert "sections" in result

@pytest.mark.asyncio
async def test_master_orchestrator_real_resume_json():
    """Verify full MasterOrchestrator JSON pipeline output on real file cv_anvi.pdf."""
    orchestrator = MasterOrchestrator()
    pdf_path = os.path.join("tests", "sample_resumes", "cv_anvi.pdf")
    
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
            
        response = await orchestrator.process_resume_pipeline(pdf_bytes, "cv_anvi.pdf")
        
        print("\n=== [Test 5 Output] MasterOrchestrator Full Pipeline JSON (cv_anvi.pdf) ===")
        print(json.dumps(response, indent=2))
        
        assert response["pipeline_stages"]["stage_1_doc_intel"] is True
        assert "document_metadata" in response
        assert "parsed_content" in response
