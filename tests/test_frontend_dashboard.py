from frontend.app import build_demo_result, normalize_analysis_payload


def test_build_demo_result_includes_expected_sections():
    result = build_demo_result(
        "Senior Python Engineer",
        "Python, Azure, FastAPI, SQL",
        "John Doe",
    )

    assert "doc_summary" in result
    assert "pii_summary" in result
    assert "ats_analysis" in result
    assert "jd_match" in result
    assert result["ats_analysis"]["ats_score"] >= 0
    assert result["jd_match"]["match_percentage"] >= 0.0


def test_normalize_analysis_payload_accepts_api_response():
    payload = {
        "doc_summary": {"raw_text": "Resume summary", "page_count": 1, "tables": [], "file_type": "pdf"},
        "pii_summary": {"clean_text": "[NAME] is a Python developer", "detected_pii": [{"type": "Person", "text": "John Doe", "confidence": 0.99}], "extracted_skills": ["Python"], "extracted_certifications": []},
        "ats_analysis": {"ats_score": 92, "strengths": ["Strong Python"], "weaknesses": [], "star_rewrites": [{"original": "Built APIs", "improved_star": "Built APIs that reduced latency", "impact_metric": "40% faster"}], "format_issues": []},
        "jd_match": {"match_percentage": 86.5, "matched_skills": ["Python"], "missing_skills": ["Azure"], "recommendations": ["Add Azure"]},
    }

    normalized = normalize_analysis_payload(payload)

    assert normalized["ats_score"] == 92
    assert normalized["jd_match_percent"] == 86.5
    assert normalized["matched_skills"] == ["Python"]
    assert normalized["missing_skills"] == ["Azure"]
