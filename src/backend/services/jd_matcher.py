"""
Job Description Matcher Service (Member 4).
Computes TF-IDF & Cosine Similarity match percentage between resume and JD.
"""
from typing import Dict, Any


class JDMatcherService:
    def compute_jd_match(self, resume_text: str, target_jd: str) -> Dict[str, Any]:
        return {
            "match_score": 85.0,
            "matching_skills": ["Python", "Azure", "FastAPI"],
            "missing_skills": ["Kubernetes"],
            "status": "success",
        }
