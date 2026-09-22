"""
Agent Function Tools for Resume Doctor (Azure AI-103).

Each of the four AI-103 modules is surfaced to the supervisor agent as a
JSON *FunctionTool*.  The agent (GPT-4.x via the Foundry Agent Service) decides
when to call these tools and with what arguments — this is the real agent loop
that replaces the previous hardcoded ``asyncio.gather`` orchestration.
"""

from __future__ import annotations

import asyncio
import re
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from azure.ai.projects.models import FunctionTool

from src.backend.config import settings
from src.backend.services.doc_intelligence import DocIntelligenceService
from src.backend.services.ai_language import AILanguageService
from src.backend.services.azure_openai import AzureOpenAIService
from src.backend.services.jd_matcher import JDMatcherService


# =====================================================================
# Per-request context: the function tools receive only JSON arguments,
# so request-scoped binary/external data (uploaded file bytes) is carried
# on a context object set by the supervisor service for each run.
# =====================================================================
@dataclass
class ToolContext:
    file_bytes: bytes = b""
    filename: str = "resume.pdf"
    target_jd: str = ""
    target_role: str = ""

    doc_service: Optional[DocIntelligenceService] = None
    language_service: Optional[AILanguageService] = None
    openai_service: Optional[AzureOpenAIService] = None
    jd_matcher_service: Optional[JDMatcherService] = None


# =====================================================================
# Module 1: Document Intelligence (layout, tables, raw text)
# =====================================================================
def tool_parse_resume(args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
    """Parse a resume file into raw text, page count, tables and sections."""
    filename = ctx.filename
    result = ctx.doc_service.parse_resume(ctx.file_bytes, filename)
    return result


# =====================================================================
# Module 2: Azure AI Language — PII Redaction + skill/cert NER
# =====================================================================
def tool_redact_pii(args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
    """Redact PII from resume text and extract skills + certifications."""
    text = args.get("text") or args.get("clean_text") or ""
    if not text:
        return {"clean_text": "", "detected_pii": [], "extracted_skills": [], "extracted_certifications": []}
    result = asyncio.run(ctx.language_service.redact_pii_and_extract_entities(text))
    return result.model_dump()


# =====================================================================
# Module 3: Azure OpenAI — ATS score + STAR bullet rewriting
# =====================================================================
_ACTION_STARTERS = [
    "built", "engineered", "designed", "implemented", "created", "managed", "led", "automated",
    "optimized", "architected", "integrated", "deployed", "maintained", "analyzed", "reduced",
    "increased", "spearheaded", "improved", "scaled", "trained", "configured", "utilized",
    "developed", "crafted", "achieved", "executed", "pioneered", "refactored",
]

_SKIP_KEYWORDS = [
    "resume", "curriculum", "cv", "@", "[email]", "[phone]", "[address]", "[name]", "[ssn]",
    "[organization]", "address", "location", "bachelor", "master", "phd", "degree", "university",
    "college", "school", "education", "skills", "summary", "contact", "github.com", "linkedin.com",
    "http", "www", "cgpa", "gpa", "coursework", "certifications", "achievements",
]


def _extract_candidate_bullets(clean_text: str, limit: int = 5) -> List[str]:
    """Extract up to ``limit`` action-verb starter senior-experience bullet lines."""
    candidates: List[str] = []
    for raw_line in clean_text.splitlines():
        line = raw_line.strip(" -*•·\t\r")
        if not line:
            continue
        lower = line.lower()
        first_word = lower.split()[0] if lower.split() else ""
        if not any(line.lower().startswith(st) or first_word == st for st in _ACTION_STARTERS):
            continue
        if re.search(r"\[[A-Z_]+\]", line):
            continue
        if "|" in line or len(line) < 28 or line.endswith(":"):
            continue
        if any(kw in lower for kw in _SKIP_KEYWORDS):
            continue
        candidates.append(line)
        if len(candidates) >= limit:
            break
    return candidates


def tool_score_ats(args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
    """Score a resume against ATS rubric and produce STAR rewrites for weak bullets."""
    resume_text = args.get("resume_text") or args.get("clean_text") or ""
    target_jd = args.get("target_jd") or ctx.target_jd or ""

    ats = ctx.openai_service.analyze_ats(resume_text, target_jd)

    bullets = _extract_candidate_bullets(resume_text)
    star_batch = ctx.openai_service.rewrite_star_bullets(bullets, target_jd)

    star_rewrites = [
        {
            "original_bullet": item.original_bullet,
            "rewritten_bullet": item.rewritten_bullet,
            "metrics_added": item.metrics_added,
            "improvement_notes": item.improvement_notes,
        }
        for item in star_batch.rewrites
    ]

    out = ats.model_dump()
    out["star_rewrites"] = star_rewrites
    out["ats_score"] = out.get("overall_score", 0)
    return out


# =====================================================================
# Module 4: JD Matcher — TF-IDF Cosine Similarity + skill gap analysis
# =====================================================================
def tool_match_jd(args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
    """Match a cleaned resume against a job description (TF-IDF + skill gap)."""
    clean_text = args.get("clean_text") or args.get("resume_text") or ""
    jd_text = args.get("jd_text") or args.get("job_description") or ctx.target_jd or ""
    resume_skills = args.get("resume_skills") or []
    if not isinstance(resume_skills, list):
        resume_skills = []

    result = ctx.jd_matcher_service.match(clean_text, jd_text, resume_skills)
    return result.model_dump()


# =====================================================================
# Tool registry: JSON-schema definitions + dispatch mapping
# =====================================================================
def _function_tool(name: str, description: str, parameters: Dict[str, Any]) -> FunctionTool:
    return FunctionTool(
        name=name,
        description=description,
        parameters=parameters,
        strict=True,
    )


def build_tool_definitions() -> List[FunctionTool]:
    """Azure Agent SDK FunctionTool list registered on the supervisor agent."""
    return [
        _function_tool(
            name="parse_resume",
            description=(
                "Parse the user-uploaded resume file. Returns the extracted raw text, page count, "
                "tables and structured sections. Call FIRST before any other tool."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Name of the uploaded resume file (e.g. resume.pdf)."}
                },
                "required": ["filename"],
                "additionalProperties": False,
            },
        ),
        _function_tool(
            name="redact_pii",
            description=(
                "Redact sensitive personally identifiable information (PII) from resume text and "
                "extract detected skills and certifications. Takes the raw resume text."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Raw resume text returned by parse_resume."}
                },
                "required": ["text"],
                "additionalProperties": False,
            },
        ),
        _function_tool(
            name="score_ats",
            description=(
                "Score the clean resume text against the 5-category ATS rubric and rewrite weak "
                "bullets into STAR format. Returns overall_score, category breakdown, strengths, "
                "improvements, missing_keywords and star_rewrites."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "resume_text": {"type": "string", "description": "PII-redacted clean resume text."},
                    "target_jd": {"type": "string", "description": "Target job description text (pass empty string if none)."},
                },
                "required": ["resume_text", "target_jd"],
                "additionalProperties": False,
            },
        ),
        _function_tool(
            name="match_jd",
            description=(
                "Compute TF-IDF cosine similarity and skill-gap match percentage between the clean "
                "resume and the target job description. Returns match_percentage, matched_skills, "
                "missing_skills and recommendations."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "clean_text": {"type": "string", "description": "PII-redacted clean resume text."},
                    "jd_text": {"type": "string", "description": "Target job description text (pass empty string if none)."},
                    "resume_skills": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of skills extracted from the resume.",
                    },
                },
                "required": ["clean_text", "jd_text", "resume_skills"],
                "additionalProperties": False,
            },
        ),
    ]


def build_tool_specs_raw() -> List[Dict[str, Any]]:
    """OpenAI Responses-API compatible tool dicts (used for a plain model client path)."""
    specs = []
    for tool in build_tool_definitions():
        specs.append(
            {
                "type": "function",
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
                "strict": True,
            }
        )
    return specs


def execute_tool(name: str, args: Dict[str, Any], ctx: ToolContext) -> Dict[str, Any]:
    """Dispatch a function-call item to the matching module implementation."""
    dispatcher = {
        "parse_resume": tool_parse_resume,
        "redact_pii": tool_redact_pii,
        "score_ats": tool_score_ats,
        "match_jd": tool_match_jd,
    }
    if name not in dispatcher:
        raise ValueError(f"Unknown tool requested by agent: {name}")
    out = dispatcher[name](args or {}, ctx)
    return out


def build_default_context() -> ToolContext:
    """Build a ToolContext wired to the four Azure service singletons."""
    return ToolContext(
        doc_service=DocIntelligenceService(),
        language_service=AILanguageService(),
        openai_service=AzureOpenAIService(),
        jd_matcher_service=JDMatcherService(),
    )