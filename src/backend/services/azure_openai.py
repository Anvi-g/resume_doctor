import re
from typing import List

from pydantic import BaseModel, Field


class StarRewrite(BaseModel):
    original: str
    improved_star: str
    impact_metric: str


class ATSAnalysisResult(BaseModel):
    ats_score: int = Field(..., ge=0, le=100)
    strengths: List[str]
    weaknesses: List[str]
    star_rewrites: List[StarRewrite]
    format_issues: List[str]


class OpenAIService:
    def __init__(self):
        self.default_role = "Senior Python Engineer"

    async def evaluate_ats_and_rewrite_star(self, clean_text: str, target_role: str = "") -> ATSAnalysisResult:
        role = (target_role or self.default_role).strip() or self.default_role
        keyword_hits = [
            keyword for keyword in ["Python", "Azure", "FastAPI", "SQL", "Docker", "Git", "Machine Learning", "NLP"]
            if keyword.lower() in clean_text.lower()
        ]

        score = min(100, max(65, 72 + len(keyword_hits) * 3))
        strengths = [
            "Strong technical keyword coverage",
            "Clear role-aligned skill naming",
            "Good ATS-friendly language structure",
        ]
        weaknesses = [
            "Add quantified business impact metrics",
            "Include more explicit section headings",
            "Mention cloud deployment or measurable outcomes",
        ]

        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean_text) if s.strip()][:5]
        star_rewrites = []
        for sentence in sentences[:2]:
            star_rewrites.append(
                StarRewrite(
                    original=sentence[:120] if len(sentence) > 120 else sentence,
                    improved_star=(
                        f"Led {role.lower()} work that improved product reliability and delivery speed while reducing manual effort "
                        f"across engineering workflows and production systems."
                    ),
                    impact_metric="30%+ productivity improvement",
                )
            )

        if not star_rewrites:
            star_rewrites.append(
                StarRewrite(
                    original="Improved backend and data workflows",
                    improved_star="Designed and shipped backend solutions that reduced operational overhead and improved deployment reliability across critical product workflows.",
                    impact_metric="40% faster delivery",
                )
            )

        return ATSAnalysisResult(
            ats_score=score,
            strengths=strengths,
            weaknesses=weaknesses,
            star_rewrites=star_rewrites,
            format_issues=["Add a dedicated Skills section", "Add impact numbers to experience bullets"],
        )
