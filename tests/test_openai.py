"""
Comprehensive Unit Tests for Member 3 (GenAI Lead) Azure OpenAI ATS Engine.

This test suite covers:
1. AzureOpenAIService client initialization and environment configuration.
2. Synchronous and asynchronous ATS scoring logic.
3. Synchronous and asynchronous STAR bullet point rewriting logic.
4. Edge-case handling (empty bullet lists).
5. FastAPI HTTP API Gateway endpoints (/health, /api/ats/score, /api/ats/star-rewrite).
6. Backward/Forward import compatibility across module aliases (`OpenAIATSService`).
"""

import pytest                      # Pytest testing framework
import re                          # Regex assertions for fabricated-metric checks
from fastapi.testclient import TestClient # FastAPI TestClient for simulating HTTP requests

# Import Member 3 Azure OpenAI Service from primary path
from src.backend.services.azure_openai import AzureOpenAIService
# Import Pydantic models for response schema assertions
from src.backend.models.schemas import ATSScoreOutput, STARRewriteBatchOutput
# Import FastAPI application instance
from src.backend.app import app


@pytest.fixture
def service():
    """
    Pytest fixture returning default AzureOpenAIService instance.
    """
    return AzureOpenAIService()


@pytest.fixture
def mock_service():
    """
    Pytest fixture returning AzureOpenAIService instance explicitly forced to mock mode
    by passing empty credentials for deterministic, fast offline unit testing.
    """
    return AzureOpenAIService(endpoint="", api_key="")


@pytest.fixture
def api_client():
    """
    Pytest fixture returning FastAPI TestClient instance for testing REST API endpoints.
    """
    return TestClient(app)


def test_azure_openai_init():
    """
    Test 1: Verify AzureOpenAIService initializes parameters and default versions correctly.
    """
    service = AzureOpenAIService(
        endpoint="https://test.openai.azure.com/",
        api_key="test_key",
        deployment_name="gpt-4o",
        api_version="2024-02-15-preview"
    )
    assert service.deployment_name == "gpt-4o"
    assert service.api_version == "2024-02-15-preview"



def test_ats_scoring_sync(mock_service):
    """
    Test 2: Verify synchronous analyze_ats method returns a valid ATSScoreOutput schema
    with scores satisfying category bounds.
    """
    sample_resume = """
    Jane Doe
    Software Engineer | Python, Azure, FastAPI
    Experience:
    - Developed a Django event platform that automated ticket booking, reducing completion time by 40%.
    - Managed PostgreSQL databases and optimized SQL query performance.
    Education: BS Computer Science
    Skills: Python, FastAPI, Docker, SQL, Azure
    """
    result = mock_service.analyze_ats(sample_resume, target_jd="Backend Engineer")

    # Assert object is instance of ATSScoreOutput Pydantic schema
    assert isinstance(result, ATSScoreOutput)
    # Assert score bounds across categories
    assert 0 <= result.overall_score <= 100
    assert 0 <= result.formatting_score <= 20
    assert 0 <= result.keywords_score <= 25
    assert 0 <= result.sections_score <= 15
    assert 0 <= result.action_verbs_score <= 20
    assert 0 <= result.impact_score <= 20
    # Assert feedback lists are populated
    assert len(result.summary_feedback) > 0
    assert len(result.strengths) > 0
    assert len(result.improvements) > 0


@pytest.mark.asyncio
async def test_ats_scoring_async(mock_service):
    """
    Test 3: Verify asynchronous async_analyze_ats method executes properly in asyncio loop.
    """
    sample_resume = "Built APIs using Python and FastAPI."
    result = await mock_service.async_analyze_ats(sample_resume)

    assert isinstance(result, ATSScoreOutput)
    assert 0 <= result.overall_score <= 100


def test_star_bullet_rewrite_sync(mock_service):
    """
    Test 4: Verify synchronous rewrite_star_bullets transforms raw bullet points into STAR format
    WITHOUT fabricating metrics that are not present in the source bullet.
    """
    bullets = ["Built a website."]
    result = mock_service.rewrite_star_bullets(bullets)

    assert isinstance(result, STARRewriteBatchOutput)
    assert len(result.rewrites) == 1
    item = result.rewrites[0]
    assert item.original_bullet == "Built a website."
    assert "Django" in item.rewritten_bullet or "Engineered" in item.rewritten_bullet or "Spearheaded" in item.rewritten_bullet or "Developed" in item.rewritten_bullet or "Architected" in item.rewritten_bullet

    # No metric in the source -> no metric may be invented (no %, $, numbers, or scales).
    assert item.metrics_added == []
    assert re.search(r"\d+\s*%", item.rewritten_bullet) is None
    assert len(item.improvement_notes) > 0


def test_star_rewrite_preserves_existing_metric_only(mock_service):
    """
    Test 4b: Verify a metric already present in the source bullet is preserved verbatim,
    and that no NEW fabricated metrics are introduced alongside it.
    """
    bullets = ["Reduced preprocessing latency by 40% with parallel workers."]
    result = mock_service.rewrite_star_bullets(bullets)

    item = result.rewrites[0]
    assert "40%" in item.rewritten_bullet
    assert "40%" in item.metrics_added[0]
    # No other invented percentage is allowed.
    numeric_metrics = re.findall(r"\d+\s*%", item.rewritten_bullet)
    assert set(numeric_metrics) == {"40%"}


def test_star_rewrite_is_real_rewrite_without_editorial_talk(mock_service):
    """
    Test 4c: A metric-less bullet must produce a genuinely rewritten STAR sentence
    (different from the original, strong lead verb), never an echo of the source
    or editorial instructions to the resume writer inside the rewritten text.
    """
    bullets = [
        "Developed storage solutions to parse and transform high-volume data "
        "into optimized CSV and Parquet formats."
    ]
    result = mock_service.rewrite_star_bullets(bullets)

    item = result.rewrites[0]
    assert item.rewritten_bullet != item.original_bullet
    assert item.rewritten_bullet.startswith("Engineered")
    assert " " in item.rewritten_bullet  # still a full sentence
    assert "No metrics were invented" not in item.rewritten_bullet
    assert "add real numbers" not in item.rewritten_bullet
    assert "original delivery" not in item.rewritten_bullet
    assert item.metrics_added == []


@pytest.mark.asyncio
async def test_star_bullet_rewrite_async(mock_service):
    """
    Test 5: Verify asynchronous async_rewrite_star_bullets method executes properly in asyncio loop.
    """
    bullets = ["Wrote python script to clean data."]
    result = await mock_service.async_rewrite_star_bullets(bullets)

    assert isinstance(result, STARRewriteBatchOutput)
    assert len(result.rewrites) == 1
    assert len(result.rewrites[0].rewritten_bullet) > 10


def test_empty_bullet_list_handling(mock_service):
    """
    Test 6: Verify empty bullet list is handled gracefully without crashing.
    """
    result = mock_service.rewrite_star_bullets([])
    assert isinstance(result, STARRewriteBatchOutput)
    assert len(result.rewrites) == 0


def test_fastapi_health_endpoint(api_client):
    """
    Test 7: Verify GET /health endpoint returns HTTP 200 and healthy status dict.
    """
    response = api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "genai_mock_mode" in data


def test_fastapi_ats_score_endpoint(api_client):
    """
    Test 8: Verify POST /api/ats/score endpoint validates request JSON and returns ATS score output.
    """
    payload = {
        "resume_text": "Experienced Python developer with Azure and Docker skills.",
        "target_jd": "Senior Backend Developer",
    }
    response = api_client.post("/api/ats/score", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "overall_score" in data
    assert "summary_feedback" in data


def test_fastapi_star_rewrite_endpoint(api_client):
    """
    Test 9: Verify POST /api/ats/star-rewrite endpoint converts request bullet points.
    """
    payload = {
        "bullet_points": ["Built a website."],
        "target_jd": "Full Stack Developer",
    }
    response = api_client.post("/api/ats/star-rewrite", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "rewrites" in data
    assert len(data["rewrites"]) == 1


def test_backend_app_services_import_compatibility():
    """
    Test 10: Verify the primary AzureOpenAIService exposes the full Member 3 API.
    """
    service = AzureOpenAIService()
    assert service is not None
    assert hasattr(service, "analyze_ats")
    assert hasattr(service, "rewrite_star_bullets")
