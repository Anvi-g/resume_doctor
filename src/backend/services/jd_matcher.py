import re
from typing import List

from pydantic import BaseModel, Field


class JDMatchResult(BaseModel):
    match_percentage: float = Field(..., ge=0.0, le=100.0)
    matched_skills: List[str]
    missing_skills: List[str]
    recommendations: List[str]


class JDMatcherService:
    def __init__(self):
        self.default_skills = [
            "Python",
            "FastAPI",
            "Azure",
            "SQL",
            "Docker",
            "Git",
            "Machine Learning",
            "NLP",
        ]

    async def match_jd_with_resume(self, clean_text: str, jd_text: str, resume_skills: List[str]) -> JDMatchResult:
        jd_lower = (jd_text or "").lower()
        resume_skill_set = {skill.strip() for skill in resume_skills if skill.strip()}
        if not resume_skill_set:
            resume_skill_set = set(self.default_skills)

        matched = [skill for skill in self.default_skills if skill.lower() in jd_lower and skill in resume_skill_set]
        missing = [skill for skill in self.default_skills if skill.lower() in jd_lower and skill not in resume_skill_set]
        if not matched:
            matched = sorted(resume_skill_set.intersection(self.default_skills))
        if not missing:
            missing = [skill for skill in self.default_skills if skill not in resume_skill_set][:3]

        overlap = len(matched)
        total = max(len(self.default_skills), 1)
        percentage = min(100.0, round((overlap / total) * 100, 1))

        recommendations = []
        if missing:
            recommendations.append(f"Highlight concrete experience with {', '.join(missing[:2])}.")
        recommendations.append("Add measurable business impact metrics for each major project.")

        return JDMatchResult(
            match_percentage=percentage,
            matched_skills=matched,
            missing_skills=missing,
            recommendations=recommendations,
        )
