"""
Unit Test Suite for Module 3: Azure OpenAI ATS & STAR Rewriter Service
Tests:
1. Live End-to-end ATS evaluation using sample_resume_testing.pdf and deployed Azure OpenAI model
2. Targeted role scoring and keyword adaptation
3. Weak bullet point identification and STAR rewrite verification
4. Boundary condition tests (empty/whitespace text)
5. Pydantic contract integrity and score bounds (0-100)
"""

import asyncio
import sys
from pathlib import Path
import pypdf
import pytest

# Ensure Windows console supports Unicode output from LLMs
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.backend.services.azure_openai import (
    AzureOpenAIService,
    ATSAnalysisResult,
    StarRewrite,
    evaluate_ats_and_rewrite_star,
)


@pytest.fixture
def service():
    """Initializes AzureOpenAIService fixture."""
    return AzureOpenAIService()


@pytest.fixture
def sample_pdf_text():
    """Extracts raw text from the uploaded sample_resume_testing.pdf."""
    pdf_path = Path(__file__).parent / "sample_resumes" / "sample_resume_testing.pdf"
    assert pdf_path.exists(), f"Sample resume not found at {pdf_path}"

    reader = pypdf.PdfReader(str(pdf_path))
    raw_text = "\n".join([page.extract_text() or "" for page in reader.pages])
    assert len(raw_text.strip()) > 0, "Failed to extract text from sample PDF"
    return raw_text


def test_live_ats_evaluation_sample_pdf(service, sample_pdf_text):
    """
    Test 1: Live end-to-end evaluation using sample resume PDF and deployed model.
    Verifies:
    - ATS score is calculated (0 to 100)
    - Strengths and weaknesses are populated
    - STAR rewrites are generated with quantifiable impact metrics
    - Pydantic schema validation succeeds
    """
    result = asyncio.run(service.evaluate_ats_and_rewrite_star(sample_pdf_text, target_role="Full Stack Engineer"))

    def safe_print(msg: str):
        try:
            print(msg)
        except Exception:
            print(msg.encode("ascii", "replace").decode("ascii"))

    # --- Live Output Inspection ---
    safe_print("\n" + "=" * 75)
    safe_print(" >>> MODULE 3: AZURE OPENAI TEST OUTPUT FOR sample_resume_testing.pdf <<<")
    safe_print("=" * 75)
    safe_print(f"\n[+] ATS COMPATIBILITY SCORE: {result.ats_score} / 100")
    safe_print("\n[+] IDENTIFIED STRENGTHS:")
    for s in result.strengths:
        safe_print(f"    * {s}")
    safe_print("\n[+] IDENTIFIED WEAKNESSES:")
    for w in result.weaknesses:
        safe_print(f"    * {w}")
    safe_print("\n[+] STAR BULLET POINT REWRITES:")
    for i, rewrite in enumerate(result.star_rewrites, 1):
        safe_print(f"    --- Rewrite #{i} ---")
        safe_print(f"    [ORIGINAL]     : {rewrite.original}")
        safe_print(f"    [IMPROVED STAR]: {rewrite.improved_star}")
        safe_print(f"    [IMPACT METRIC]: {rewrite.impact_metric}")
    safe_print("\n[+] FORMAT & STRUCTURE RECOMMENDATIONS:")
    for f in result.format_issues:
        safe_print(f"    * {f}")
    safe_print("=" * 75 + "\n")

    assert isinstance(result, ATSAnalysisResult)
    assert 0 <= result.ats_score <= 100
    assert len(result.strengths) > 0
    assert len(result.weaknesses) > 0
    assert len(result.star_rewrites) > 0

    for rewrite in result.star_rewrites:
        assert isinstance(rewrite, StarRewrite)
        assert len(rewrite.original.strip()) > 0
        assert len(rewrite.improved_star.strip()) > 0
        assert len(rewrite.impact_metric.strip()) > 0


def test_standalone_function_call(sample_pdf_text):
    """
    Test 2: Verifies the exact Master Project Plan function signature:
    evaluate_ats_and_rewrite_star(clean_text, target_role)
    """
    result = asyncio.run(evaluate_ats_and_rewrite_star(sample_pdf_text, target_role="Cloud Architect"))
    assert isinstance(result, ATSAnalysisResult)
    assert 0 <= result.ats_score <= 100


def test_empty_and_whitespace_input(service):
    """
    Test 3: Graceful degradation for empty or whitespace-only inputs.
    """
    result_empty = asyncio.run(service.evaluate_ats_and_rewrite_star(""))
    assert result_empty.ats_score == 0
    assert len(result_empty.weaknesses) > 0

    result_whitespace = asyncio.run(service.evaluate_ats_and_rewrite_star("   \n\t  "))
    assert result_whitespace.ats_score == 0


def test_offline_fallback_simulation():
    """
    Test 4: Verifies fallback functionality when unconfigured or offline.
    """
    unconfigured_service = AzureOpenAIService(endpoint="", key="")
    sample_text = (
        "John Doe\nSoftware Engineer with experience in Python and PostgreSQL.\n"
        "Responsible for building REST APIs and handling database migrations.\n"
        "Worked on backend bugs and maintained servers."
    )
    result = asyncio.run(unconfigured_service.evaluate_ats_and_rewrite_star(sample_text))

    assert isinstance(result, ATSAnalysisResult)
    assert 0 <= result.ats_score <= 100
    assert len(result.star_rewrites) > 0
    assert result.star_rewrites[0].improved_star != ""
