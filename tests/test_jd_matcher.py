"""
Unit Tests for Member 4 JD Matcher Service.
"""
from src.backend.services.jd_matcher import JDMatcherService


def test_jd_matcher_compute():
    service = JDMatcherService()
    result = service.compute_jd_match("Python developer", "Python Backend Role")
    assert result["status"] == "success"
    assert "match_score" in result
