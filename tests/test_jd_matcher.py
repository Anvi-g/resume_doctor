"""
Unit Test Suite for Member 4: Job Description (JD) Skill Gap Analyzer & Matcher
Tests:
1. Legacy compatibility: test_jd_matcher_compute
2. TF-IDF vectorization and Cosine Similarity math.
3. Skill extraction from varied JD formats.
4. Set-theoretic skill gap analysis (matched_skills vs missing_skills).
5. High-match candidate scoring (>70%).
6. Low-match candidate scoring (<35%).
7. Edge cases: Empty JD, empty resume text, special characters.
8. Exact async function signature: match_jd_with_resume.
"""

import pytest
import asyncio
from src.backend.services.jd_matcher import JDMatcherService, match_jd_with_resume
from src.backend.models.schemas import JDMatchResult


def test_jd_matcher_compute():
    """Verify legacy dictionary interface works as expected."""
    service = JDMatcherService()
    result = service.compute_jd_match("Python developer", "Python Backend Role")
    assert result["status"] == "success"
    assert "match_score" in result


@pytest.fixture
def matcher():
    return JDMatcherService()


def test_matcher_initialization(matcher):
    """Verify JDMatcherService initializes cleanly."""
    assert matcher is not None


def test_tfidf_cosine_similarity_high_overlap(matcher):
    """Test TF-IDF cosine similarity produces strong score for overlapping texts."""
    resume_text = (
        "Experienced Backend Developer specializing in Python, FastAPI, Docker, and PostgreSQL. "
        "Built distributed REST APIs and deployed microservices to Azure Cloud with CI/CD pipelines."
    )
    jd_text = (
        "Seeking a Senior Python Developer with strong expertise in FastAPI, PostgreSQL, and Docker. "
        "Experience building scalable REST APIs and deploying to Azure is required."
    )
    sim = matcher.compute_tfidf_cosine_similarity(resume_text, jd_text)
    assert 0.20 <= sim <= 1.0


def test_tfidf_cosine_similarity_low_overlap(matcher):
    """Test TF-IDF cosine similarity produces low score for unrelated texts."""
    resume_text = (
        "Creative Graphic Designer proficient in Adobe Photoshop, Illustrator, and typography. "
        "Designed marketing flyers, logo branding, and print advertisements for fashion retail."
    )
    jd_text = (
        "Looking for a Cloud Infrastructure DevOps Engineer with deep experience in Kubernetes, "
        "Terraform, AWS, Linux system administration, and Kafka message brokers."
    )
    sim = matcher.compute_tfidf_cosine_similarity(resume_text, jd_text)
    assert sim < 0.25


def test_extract_jd_skills(matcher):
    """Verify skill extraction from realistic Job Description text."""
    jd_text = """
    Job Title: Senior Cloud & Backend Engineer
    We are looking for a software engineer to join our cloud platform team.
    Requirements:
    - 5+ years of experience with Python, FastAPI, and PostgreSQL.
    - Hands-on experience with Docker, Kubernetes, and Azure Cloud.
    - Familiarity with CI/CD, Git, and Microservices architecture.
    """
    extracted = matcher.extract_jd_skills(jd_text)
    expected_subset = {"Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "Azure", "Git"}
    for skill in expected_subset:
        assert skill in extracted, f"Expected skill '{skill}' was not extracted from JD"


def test_skill_gap_analysis(matcher):
    """Verify accurate separation of matched vs missing skills."""
    resume_skills = ["Python", "FastAPI", "Git", "Docker", "SQL"]
    jd_skills = ["Python", "FastAPI", "Docker", "Kubernetes", "Azure", "PostgreSQL"]

    matched, missing, ratio = matcher.analyze_skill_gap(resume_skills, jd_skills)

    assert "Python" in matched
    assert "FastAPI" in matched
    assert "Docker" in matched
    assert "Kubernetes" in missing
    assert "Azure" in missing
    assert len(matched) == 3
    assert len(missing) == 3
    assert ratio == 0.5


def test_high_match_profile_scoring(matcher):
    """Verify that a highly aligned candidate receives a strong match score (>70%)."""
    resume_text = """
    Senior Python Engineer with 6 years designing and deploying cloud-native backend systems.
    Proficient in Python, FastAPI, Docker, Kubernetes, PostgreSQL, Git, and Azure.
    Led migration of monolithic application into scalable microservices architecture.
    """
    resume_skills = ["Python", "FastAPI", "Docker", "Kubernetes", "PostgreSQL", "Azure", "Git"]
    jd_text = """
    We require a Python Backend Developer with 4+ years building REST APIs with FastAPI.
    Required Skills: Python, FastAPI, PostgreSQL, Docker, Azure, Git.
    """

    result = matcher.match(resume_text, jd_text, resume_skills)
    assert isinstance(result, JDMatchResult)
    assert result.match_percentage >= 70.0
    assert len(result.matched_skills) >= 4
    assert len(result.missing_skills) == 0


def test_low_match_profile_scoring(matcher):
    """Verify that an unrelated candidate receives a low match score (<35%)."""
    resume_text = """
    Graphic designer and visual artist with expertise in Figma, Photoshop, and UI typography.
    """
    resume_skills = ["Figma", "Photoshop", "Typography"]
    jd_text = """
    Senior DevOps Engineer: Kubernetes, Terraform, Docker, Python, AWS, Prometheus, Linux.
    """

    result = matcher.match(resume_text, jd_text, resume_skills)
    assert result.match_percentage < 35.0
    assert len(result.missing_skills) >= 4


def test_edge_case_empty_jd(matcher):
    """Verify graceful handling when Job Description is empty."""
    result = matcher.match("Experienced Python developer", "", ["Python"])
    assert result.match_percentage == 0.0
    assert len(result.matched_skills) == 0


@pytest.mark.asyncio
async def test_async_contract_match_jd_with_resume():
    """Verify the exact async function signature required by the Master Project Plan."""
    clean_text = "Python engineer experienced in FastAPI and Docker."
    jd_text = "Looking for a Python and FastAPI developer."
    resume_skills = ["Python", "FastAPI"]

    res = await match_jd_with_resume(clean_text, jd_text, resume_skills)
    assert isinstance(res, JDMatchResult)
    assert res.match_percentage > 50.0
    assert "Python" in res.matched_skills
    assert "FastAPI" in res.matched_skills
