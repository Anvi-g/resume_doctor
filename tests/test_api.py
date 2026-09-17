"""
Unit and Integration Tests for Gateway API endpoints.
Member 4 Gateway Ownership:
- GET /health
- GET /api/health
- POST /api/match-jd
- POST /api/analyze
"""

import io
import pytest
from fastapi.testclient import TestClient
from src.backend.app import app
from src.backend.models.schemas import MasterAnalyzeResponse

client = TestClient(app)


def test_health():
    """Verify legacy /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root_endpoint():
    """Verify landing route provides operational status."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Resume Doctor API Gateway"
    assert data["status"] == "Operational"


def test_api_health_check_endpoint():
    """Verify /api/health reports statuses for all 4 member services."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Healthy"
    assert "modules" in data
    assert "m4_jd_matcher" in data["modules"]


def test_direct_jd_match_endpoint():
    """Verify standalone POST /api/match-jd without file upload."""
    payload = {
        "clean_text": "Experienced Python backend engineer proficient in FastAPI, Docker, and PostgreSQL.",
        "jd_text": "Requirements: Python, FastAPI, Docker, Azure, and Kubernetes.",
        "resume_skills": ["Python", "FastAPI", "Docker", "PostgreSQL"]
    }
    response = client.post("/api/match-jd", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "match_percentage" in data
    assert "matched_skills" in data
    assert "missing_skills" in data
    assert "Python" in data["matched_skills"]
    assert "FastAPI" in data["matched_skills"]
    assert "Docker" in data["matched_skills"]
    assert "Kubernetes" in data["missing_skills"]


def test_analyze_endpoint_with_mock_pdf():
    """Verify POST /api/analyze accepts PDF file and returns MasterAnalyzeResponse."""
    pdf_content = (
        b"%PDF-1.4\n"
        b"Alex Morgan\n"
        b"Software Engineer\n"
        b"Email: alex.morgan@example.com | Phone: +91 90000 00000\n"
        b"Skills: Python, FastAPI, Docker, Git, SQL\n"
        b"Experience: Developed REST APIs and microservices.\n"
    )
    mock_pdf_file = io.BytesIO(pdf_content)

    form_data = {
        "job_description": "We are seeking a Python Developer with skills in FastAPI, Docker, Git, Kubernetes, and AWS.",
        "target_role": "Python Backend Engineer"
    }
    files = {
        "resume_file": ("sample_resume.pdf", mock_pdf_file, "application/pdf")
    }

    response = client.post("/api/analyze", data=form_data, files=files)
    assert response.status_code == 200

    data = response.json()
    validated_response = MasterAnalyzeResponse(**data)
    assert validated_response.doc_summary is not None
    assert validated_response.jd_match is not None
    assert validated_response.jd_match.match_percentage > 0.0


def test_analyze_endpoint_invalid_file_extension():
    """Verify endpoint rejects invalid file formats with HTTP 400."""
    fake_exe = io.BytesIO(b"MZ executable header")
    files = {
        "resume_file": ("malicious_file.exe", fake_exe, "application/octet-stream")
    }
    response = client.post("/api/analyze", files=files, data={"job_description": "Python dev"})
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]
