"""
Unit Test Suite for Module 2: Azure AI Language & PII Redaction Engine
Tests:
1. End-to-end PDF parsing and redaction using sample_resume_testing.pdf
2. PII masking validation (guaranteeing zero email/phone leakage)
3. NER skill and certification extraction
4. Edge cases (empty text, whitespace)
5. Pydantic schema contract integrity
"""

import asyncio
from pathlib import Path
import pypdf
import pytest

from src.backend.services.ai_language import AILanguageService, RedactPIIResponse


@pytest.fixture
def service():
    """Initializes AILanguageService fixture."""
    return AILanguageService()


@pytest.fixture
def sample_pdf_text():
    """Extracts raw text from the uploaded sample_resume_testing.pdf."""
    pdf_path = Path(__file__).parent / "sample_resumes" / "sample_resume_testing.pdf"
    assert pdf_path.exists(), f"Sample resume not found at {pdf_path}"
    
    reader = pypdf.PdfReader(str(pdf_path))
    raw_text = "\n".join([page.extract_text() or "" for page in reader.pages])
    assert len(raw_text.strip()) > 0, "Failed to extract text from sample PDF"
    return raw_text


def test_redact_sample_resume_pdf(service, sample_pdf_text):
    """
    Test 1: Tests your actual uploaded sample resume PDF.
    Verifies that:
    - Email 'alex.morgan@example.com' is redacted to [EMAIL]
    - Phone number '+91 90000 00000' is redacted to [PHONE]
    - Skills ('Python', 'SQL', 'Git') are successfully extracted
    - Pydantic model contract is returned
    """
    result = asyncio.run(service.redact_pii_and_extract_entities(sample_pdf_text))

    # --- Live Output Inspection ---
    print("\n" + "=" * 70)
    print(" >>> MODULE 2: TEST OUTPUT FOR sample_resume_testing.pdf <<<")
    print("=" * 70)
    print("\n[+] CLEAN REDACTED TEXT (First 350 characters):")
    print("-" * 50)
    print(result.clean_text[:350] + "\n...")
    print("-" * 50)
    print("\n[+] DETECTED PII ENTITIES:")
    for p in result.detected_pii:
        print(f"    * {p['type']}: '{p['text']}' (Confidence: {p['confidence']})")
    print("\n[+] EXTRACTED SKILLS:")
    print(f"    {result.extracted_skills}")
    print("\n[+] EXTRACTED CERTIFICATIONS:")
    print(f"    {result.extracted_certifications}")
    print("=" * 70 + "\n")

    assert isinstance(result, RedactPIIResponse)
    assert len(result.clean_text) > 0

    # Privacy Assertions (Zero Leakage)
    assert "alex.morgan@example.com" not in result.clean_text, "Email leaked in clean text!"
    assert "+91 90000 00000" not in result.clean_text, "Phone number leaked in clean text!"
    assert "[EMAIL]" in result.clean_text, "[EMAIL] placeholder missing from clean text!"
    assert "[PHONE]" in result.clean_text, "[PHONE] placeholder missing from clean text!"

    # PII Metadata Assertions
    detected_types = [p["type"] for p in result.detected_pii]
    assert "Email" in detected_types
    assert "PhoneNumber" in detected_types

    # Skill Extraction Assertions
    assert len(result.extracted_skills) > 0
    assert any(skill in result.extracted_skills for skill in ["Python", "SQL", "Git", "JavaScript"])



def test_direct_text_pii_masking(service):
    """
    Test 2: Verifies PII detection on inline text with multiple identifiers.
    """
    sample_text = (
        "Candidate Jane Smith. Contact: jane.smith@domain.org or +1 (555) 234-5678. "
        "Experienced Senior Engineer proficient in Docker, Python, and Kubernetes. "
        "Certified: AWS Certified Solutions Architect."
    )
    result = asyncio.run(service.redact_pii_and_extract_entities(sample_text))

    assert "jane.smith@domain.org" not in result.clean_text
    assert "[EMAIL]" in result.clean_text
    assert "[PHONE]" in result.clean_text
    assert "Python" in result.extracted_skills
    assert "Docker" in result.extracted_skills
    assert "AWS Certified" in result.extracted_certifications


def test_empty_and_whitespace_input(service):
    """
    Test 3: Graceful degradation for empty or whitespace-only inputs.
    """
    result_empty = asyncio.run(service.redact_pii_and_extract_entities(""))
    assert result_empty.clean_text == ""
    assert result_empty.detected_pii == []
    assert result_empty.extracted_skills == []
    assert result_empty.extracted_certifications == []

    result_whitespace = asyncio.run(service.redact_pii_and_extract_entities("   \n\t  "))
    assert result_whitespace.clean_text == ""


def test_pydantic_schema_serialization(service):
    """
    Test 4: Verifies serialization compatibility with downstream FastAPI and GenAI modules.
    """
    result = asyncio.run(
        service.redact_pii_and_extract_entities("Developer with Python skills. Email: dev@test.com")
    )
    # Ensure serialization to dict works without errors
    dumped = result.model_dump()
    assert "clean_text" in dumped
    assert "detected_pii" in dumped
    assert "extracted_skills" in dumped
    assert "extracted_certifications" in dumped
