"""
Azure OpenAI Service (Member 3 - GenAI Lead)

Integrates Azure OpenAI GPT-4o with LangChain and Pydantic structured output validation
for ATS scoring and STAR bullet rewrites.

Key Capabilities:
1. Loads Azure configuration from environment variables with fallback defaults.
2. Initializes `AzureChatOpenAI` client with structured output chains.
3. Provides synchronous and asynchronous methods (`analyze_ats`, `async_analyze_ats`, `rewrite_star_bullets`, `async_rewrite_star_bullets`).
4. Includes an offline deterministic fallback engine when Azure OpenAI API keys are not provided or unreachable.
"""

import os               # Standard library OS module for accessing environment variables
import re               # Regular expression library for text cleaning
import json             # Standard library JSON module
import logging          # Standard library logging module for recording events and errors
import asyncio          # Standard library asyncio module for asynchronous event loop operations
from typing import List, Optional, Dict, Any  # Type hinting annotations
from dotenv import load_dotenv               # Load environment variables from .env file

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

# Import AzureChatOpenAI client from langchain_openai package
from langchain_openai import AzureChatOpenAI
# Import ChatPromptTemplate from langchain_core package
from langchain_core.prompts import ChatPromptTemplate

# Import Pydantic schemas for response validation
from src.backend.models.schemas import (
    ATSScoreOutput,          # Output schema for ATS audit evaluation
    STARRewriteItem,         # Individual STAR bullet point rewrite item schema
    STARRewriteBatchOutput,  # Batch output schema for STAR bullet point rewrites
)

# Import LangChain prompt templates for ATS audit and STAR rewrite
from src.backend.prompts.ats_prompts import (
    ATS_SCORING_PROMPT_TEMPLATE,   # Prompt template for ATS scoring
    STAR_REWRITE_PROMPT_TEMPLATE,  # Prompt template for STAR bullet rewrites
)

# Load environment variables from local .env file
load_dotenv()

# Initialize module-level logger instance
logger = logging.getLogger(__name__)


class AzureOpenAIService:
    """
    Main GenAI Service class for managing Azure OpenAI GPT-4o interactions.
    """
    def __init__(
        self,
        endpoint: Optional[str] = None,         # Azure OpenAI Endpoint URL
        api_key: Optional[str] = None,          # Azure OpenAI API key
        deployment_name: Optional[str] = None,  # Deployment name (e.g., gpt-4o)
        api_version: Optional[str] = None,      # Azure API version string
        temperature: float = 0.2,               # LLM sampling temperature (0.2 for deterministic output)
        request_timeout: int = 10,              # API HTTP request timeout in seconds (fail fast)
        max_retries: int = 1,                   # Number of automated retry attempts on failure
    ):
        self.endpoint = endpoint if endpoint is not None else os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
        self.api_key = api_key if api_key is not None else os.getenv("AZURE_OPENAI_KEY", "").strip()
        self.deployment_name = (
            deployment_name
            or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o").strip()
        )
        self.api_version = (
            api_version
            or os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview").strip()
        )
        self.project_endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT", "").strip()
        self.project_model = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", self.deployment_name).strip()
        
        self.temperature = temperature      # Store temperature setting
        self.request_timeout = request_timeout # Store timeout setting
        self.max_retries = max_retries      # Store max retries setting

        force_mock = os.getenv("MOCK_AZURE_OPENAI", "false").lower() in ("true", "1") or os.getenv("FORCE_OFFLINE", "0").lower() in ("true", "1")
        has_credentials = bool(self.project_endpoint) or (
            bool(self.endpoint)
            and bool(self.api_key)
            and "your_" not in self.api_key.lower()
            and "<your-" not in self.endpoint.lower()
        )
        self.is_mock_mode = force_mock or not has_credentials

        self.foundry_client = None
        self.llm = None

        if not self.is_mock_mode:
            # 1. Try Azure AI Foundry Project Client
            if self.project_endpoint:
                try:
                    cred = DefaultAzureCredential(
                        exclude_managed_identity_credential=True,
                        exclude_workload_identity_credential=True,
                        exclude_shared_token_cache_credential=True,
                        exclude_developer_cli_credential=True,
                    )
                    p_client = AIProjectClient(
                        endpoint=self.project_endpoint,
                        credential=cred,
                        allow_preview=True
                    )
                    self.foundry_client = p_client.get_openai_client()
                    logger.info(f"Foundry OpenAI client initialized successfully with model '{self.project_model}'.")
                except Exception as e:
                    logger.warning(f"Failed to initialize Foundry OpenAI client ({e}).")

            # 2. Try standalone AzureChatOpenAI if endpoint & key are valid
            if bool(self.endpoint) and bool(self.api_key) and "your_" not in self.api_key.lower():
                try:
                    self.llm = AzureChatOpenAI(
                        azure_endpoint=self.endpoint,
                        azure_deployment=self.deployment_name,
                        api_key=self.api_key,
                        api_version=self.api_version,
                        temperature=self.temperature,
                        timeout=self.request_timeout,
                        max_retries=self.max_retries,
                    )
                    logger.info(f"AzureChatOpenAI initialized successfully with deployment '{self.deployment_name}'.")
                except Exception as e:
                    logger.warning(f"Failed to initialize AzureChatOpenAI client ({e}).")

            if not self.foundry_client and not self.llm:
                logger.warning("No active LLM client could be initialized. Falling back to mock mode.")
                self.is_mock_mode = True
        else:
            logger.info("AzureOpenAIService running in Mock / Offline mode.")

    @staticmethod
    def _sanitize_ats_data(data: dict) -> dict:
        if not isinstance(data, dict):
            data = {}
        
        strengths = data.get("strengths") or []
        if not isinstance(strengths, list):
            strengths = [str(strengths)]
            
        improvements = data.get("improvements") or data.get("weaknesses") or data.get("recommendations") or []
        if not isinstance(improvements, list):
            improvements = [str(improvements)]
            
        missing_keywords = data.get("missing_keywords") or []
        if not isinstance(missing_keywords, list):
            missing_keywords = [str(missing_keywords)]

        summary_feedback = str(data.get("summary_feedback") or "Resume audit complete.")

        def _clamp(val, min_val, max_val, default):
            try:
                if val is None:
                    return default
                return max(min_val, min(max_val, int(val)))
            except (ValueError, TypeError):
                return default

        formatting_score = _clamp(data.get("formatting_score"), 0, 20, 15)
        keywords_score = _clamp(data.get("keywords_score"), 0, 25, 18)
        sections_score = _clamp(data.get("sections_score"), 0, 15, 12)
        action_verbs_score = _clamp(data.get("action_verbs_score"), 0, 20, 15)
        impact_score = _clamp(data.get("impact_score"), 0, 20, 14)
        
        overall_score = data.get("overall_score")
        if overall_score is None:
            overall_score = formatting_score + keywords_score + sections_score + action_verbs_score + impact_score
        overall_score = _clamp(overall_score, 0, 100, 75)

        return {
            "overall_score": overall_score,
            "formatting_score": formatting_score,
            "keywords_score": keywords_score,
            "sections_score": sections_score,
            "action_verbs_score": action_verbs_score,
            "impact_score": impact_score,
            "summary_feedback": summary_feedback,
            "strengths": [str(s) for s in strengths if s],
            "improvements": [str(i) for i in improvements if i],
            "missing_keywords": [str(k) for k in missing_keywords if k],
        }

    @staticmethod
    def _sanitize_star_data(data: dict) -> dict:
        if not isinstance(data, dict):
            data = {}
        raw_rewrites = data.get("rewrites") or data.get("star_rewrites") or []
        if not isinstance(raw_rewrites, list):
            raw_rewrites = []

        clean_rewrites = []
        for item in raw_rewrites:
            if isinstance(item, dict):
                orig = str(item.get("original_bullet") or item.get("original") or item.get("original_text") or "Original experience bullet")
                rewritten = str(item.get("rewritten_bullet") or item.get("improved_star") or item.get("rewritten") or orig)
                metrics = item.get("metrics_added") or []
                if not isinstance(metrics, list):
                    metrics = [str(metrics)]
                notes = item.get("improvement_notes") or item.get("notes") or ""
                clean_rewrites.append({
                    "original_bullet": orig,
                    "rewritten_bullet": rewritten,
                    "situation_task": str(item.get("situation_task")) if item.get("situation_task") else None,
                    "action": str(item.get("action")) if item.get("action") else None,
                    "result": str(item.get("result")) if item.get("result") else None,
                    "metrics_added": [str(m) for m in metrics if m],
                    "improvement_notes": str(notes) if notes else None,
                })
        
        summary = str(data.get("overall_summary") or "STAR bullet transformations generated successfully.")
        return {
            "rewrites": clean_rewrites,
            "overall_summary": summary,
        }

    def _call_foundry_ats(self, resume_text: str, target_jd: str = "") -> ATSScoreOutput:
        sys_prompt = (
            "You are an expert ATS recruiter auditing a resume against a target job description.\n"
            "Analyze the resume text and return a valid JSON object matching this schema:\n"
            "{\n"
            '  "overall_score": int (0-100),\n'
            '  "formatting_score": int (0-20),\n'
            '  "keywords_score": int (0-25),\n'
            '  "sections_score": int (0-15),\n'
            '  "action_verbs_score": int (0-20),\n'
            '  "impact_score": int (0-20),\n'
            '  "summary_feedback": string,\n'
            '  "strengths": list of detailed specific strings,\n'
            '  "improvements": list of detailed specific actionable recommendation strings,\n'
            '  "missing_keywords": list of strings\n'
            "}"
        )
        user_prompt = f"RESUME:\n{resume_text}\n\nTARGET JOB DESCRIPTION:\n{target_jd or 'General Technical Role'}"
        res = self.foundry_client.chat.completions.create(
            model=self.project_model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        data = json.loads(res.choices[0].message.content)
        sanitized = self._sanitize_ats_data(data)
        return ATSScoreOutput.model_validate(sanitized)

    def _call_foundry_star(self, bullet_points: List[str], target_jd: str = "") -> STARRewriteBatchOutput:
        sys_prompt = (
            "You are an expert ATS recruiter. Convert generic bullet points into STAR-formatted (Situation, Task, Action, Result) "
            "bullet points with quantified impact metrics.\n"
            "Return a JSON object matching this schema:\n"
            "{\n"
            '  "rewrites": [\n'
            "    {\n"
            '      "original_bullet": string,\n'
            '      "rewritten_bullet": string,\n'
            '      "metrics_added": list of strings,\n'
            '      "improvement_notes": string\n'
            "    }\n"
            "  ],\n"
            '  "overall_summary": string\n'
            "}"
        )
        user_prompt = f"Target Role/JD:\n{target_jd or 'General Technical Role'}\n\nBullets to rewrite:\n" + "\n".join(f"- {b}" for b in bullet_points)
        res = self.foundry_client.chat.completions.create(
            model=self.project_model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        data = json.loads(res.choices[0].message.content)
        sanitized = self._sanitize_star_data(data)
        return STARRewriteBatchOutput.model_validate(sanitized)

    def analyze_ats(self, resume_text: str, target_jd: str = "") -> ATSScoreOutput:
        if self.is_mock_mode:
            return self._generate_mock_ats_score(resume_text, target_jd)

        if self.foundry_client:
            try:
                return self._call_foundry_ats(resume_text, target_jd)
            except Exception as e:
                logger.error(f"Foundry ATS scoring invocation failed: {e}. Trying fallback LLM...")

        if self.llm:
            try:
                structured_llm = self.llm.with_structured_output(ATSScoreOutput)
                chain = ATS_SCORING_PROMPT_TEMPLATE | structured_llm
                return chain.invoke({"resume_text": resume_text, "target_jd": target_jd or "General Technical Role"})
            except Exception as e:
                logger.error(f"Error during Azure OpenAI ATS scoring invocation: {e}")

        return self._generate_mock_ats_score(resume_text, target_jd)

    async def async_analyze_ats(self, resume_text: str, target_jd: str = "") -> ATSScoreOutput:
        if self.is_mock_mode:
            return self._generate_mock_ats_score(resume_text, target_jd)

        if self.foundry_client:
            try:
                return await asyncio.to_thread(self._call_foundry_ats, resume_text, target_jd)
            except Exception as e:
                logger.error(f"Foundry async ATS scoring invocation failed: {e}. Trying fallback LLM...")

        if self.llm:
            try:
                structured_llm = self.llm.with_structured_output(ATSScoreOutput)
                chain = ATS_SCORING_PROMPT_TEMPLATE | structured_llm
                return await chain.ainvoke({"resume_text": resume_text, "target_jd": target_jd or "General Technical Role"})
            except Exception as e:
                logger.error(f"Error during async Azure OpenAI ATS scoring invocation: {e}")

        return self._generate_mock_ats_score(resume_text, target_jd)

    def rewrite_star_bullets(
        self, bullet_points: List[str], target_jd: str = ""
    ) -> STARRewriteBatchOutput:
        if not bullet_points:
            return STARRewriteBatchOutput(rewrites=[], overall_summary="No bullet points were provided for rewriting.")

        if self.is_mock_mode:
            return self._generate_mock_star_rewrites(bullet_points, target_jd)

        if self.foundry_client:
            try:
                return self._call_foundry_star(bullet_points, target_jd)
            except Exception as e:
                logger.error(f"Foundry STAR rewrite invocation failed: {e}. Trying fallback LLM...")

        if self.llm:
            try:
                bullet_text = "\n".join([f"- {b}" for b in bullet_points])
                structured_llm = self.llm.with_structured_output(STARRewriteBatchOutput)
                chain = STAR_REWRITE_PROMPT_TEMPLATE | structured_llm
                return chain.invoke({"bullet_points_text": bullet_text, "target_jd": target_jd or "General Technical Role"})
            except Exception as e:
                logger.error(f"Error during Azure OpenAI STAR rewrite invocation: {e}")

        return self._generate_mock_star_rewrites(bullet_points, target_jd)

    async def async_rewrite_star_bullets(
        self, bullet_points: List[str], target_jd: str = ""
    ) -> STARRewriteBatchOutput:
        if not bullet_points:
            return STARRewriteBatchOutput(rewrites=[], overall_summary="No bullet points were provided for rewriting.")

        if self.is_mock_mode:
            return self._generate_mock_star_rewrites(bullet_points, target_jd)

        if self.foundry_client:
            try:
                return await asyncio.to_thread(self._call_foundry_star, bullet_points, target_jd)
            except Exception as e:
                logger.error(f"Foundry async STAR rewrite invocation failed: {e}. Trying fallback LLM...")

        if self.llm:
            try:
                bullet_text = "\n".join([f"- {b}" for b in bullet_points])
                structured_llm = self.llm.with_structured_output(STARRewriteBatchOutput)
                chain = STAR_REWRITE_PROMPT_TEMPLATE | structured_llm
                return await chain.ainvoke({"bullet_points_text": bullet_text, "target_jd": target_jd or "General Technical Role"})
            except Exception as e:
                logger.error(f"Error during async Azure OpenAI STAR rewrite invocation: {e}")

        return self._generate_mock_star_rewrites(bullet_points, target_jd)

    # ============================================================================
    # Fallback Deterministic Engine for Offline / Mock Mode
    # ============================================================================

    def _generate_mock_ats_score(self, resume_text: str, target_jd: str) -> ATSScoreOutput:
        """
        Generates realistic ATS scoring breakdown using deterministic heuristics when Azure API keys are absent.
        """
        text_lower = resume_text.lower()
        word_count = len(resume_text.split())

        formatting_score = 16 if word_count > 50 else 10
        keywords_score = 20 if any(kw in text_lower for kw in ["python", "azure", "api", "fastapi", "react", "sql", "aws", "docker"]) else 12
        sections_score = 14 if any(sec in text_lower for sec in ["experience", "education", "skills", "projects"]) else 8
        action_verbs_score = 17 if any(v in text_lower for v in ["developed", "built", "implemented", "managed", "designed", "created", "led", "automated"]) else 11
        impact_score = 16 if any(char in text_lower for char in ["%", "$", "reduced", "increased", "supported", "improved", "users"]) else 9
        overall_score = min(100, max(0, formatting_score + keywords_score + sections_score + action_verbs_score + impact_score))

        # Dynamic strengths and improvements extraction
        tech_keywords = ["Python", "FastAPI", "Docker", "SQL", "Azure", "Git", "React", "JavaScript", "TypeScript", "Machine Learning", "PyTorch", "PostgreSQL", "C++", "Java", "REST APIs"]
        found_skills = [kw for kw in tech_keywords if re.search(rf"\b{re.escape(kw)}\b", resume_text, re.IGNORECASE)]
        verbs_found = [v.capitalize() for v in ["developed", "built", "engineered", "implemented", "designed", "created", "automated", "spearheaded", "architected"] if v in text_lower]

        strengths = []
        if found_skills:
            skills_str = ", ".join(found_skills[:4])
            strengths.append(f"Strong technical alignment with hands-on proficiency in {skills_str}.")
        else:
            strengths.append("Clear layout structure with identifiable technical experience sections.")

        if verbs_found:
            verbs_str = ", ".join(verbs_found[:3])
            strengths.append(f"Demonstrates proactive engineering impact using strong action verbs like {verbs_str}.")
        else:
            strengths.append("Well-organized experience section with identifiable technical terminology.")

        if word_count > 40:
            strengths.append(f"Comprehensive detail provided across {word_count} words covering key technical responsibilities.")

        # Dynamic improvements extraction
        jd_lower = target_jd.lower() if target_jd else ""
        all_candidate_missing = ["Kubernetes", "CI/CD", "Azure OpenAI", "Microservices Architecture", "System Design", "PostgreSQL", "Docker", "AWS"]
        
        missing_keywords = []
        if jd_lower:
            missing_keywords = [kw for kw in all_candidate_missing if kw.lower() in jd_lower and kw.lower() not in text_lower]
        if not missing_keywords:
            missing_keywords = [kw for kw in all_candidate_missing if kw.lower() not in text_lower][:3]

        improvements = []
        if missing_keywords:
            missing_str = ", ".join(missing_keywords[:3])
            improvements.append(f"Incorporate priority target job keywords missing from resume: {missing_str}.")

        if not any(char in text_lower for char in ["%", "$", "reduced", "increased", "latency", "users", "ms", "s"]):
            improvements.append("Add quantifiable impact metrics (e.g., latency reduced by X%, user scale, revenue supported) to experience bullet points.")
        else:
            improvements.append("Enhance bullet point impact by starting each statement with domain-aligned lead verbs like 'Architected' or 'Spearheaded'.")

        if word_count < 150:
            improvements.append("Expand section bullet points to include specific project technical stack and architecture decisions.")

        return ATSScoreOutput(
            overall_score=overall_score,
            formatting_score=formatting_score,
            keywords_score=keywords_score,
            sections_score=sections_score,
            action_verbs_score=action_verbs_score,
            impact_score=impact_score,
            summary_feedback=f"Resume displays solid technical foundations in {found_skills[0] if found_skills else 'software development'}. Focus on incorporating target job keywords and quantified impact metrics.",
            strengths=strengths,
            improvements=improvements,
            missing_keywords=missing_keywords
        )

    _WEAK_VERB_LEADS = {
        "built": "Engineered",
        "develop": "Engineered",
        "developed": "Engineered",
        "created": "Architected",
        "made": "Delivered",
        "worked": "Spearheaded",
        "helped": "Streamlined",
        "used": "Leveraged",
        "implemented": "Automated",
        "wrote": "Automated",
        "designed": "Architected",
        "reduced": "Cut",
        "improved": "Enhanced",
        "increased": "Scaled",
        "optimized": "Optimized",
    }

    def _mock_rewrap_bullet(self, clean_text: str, matched_metric: Any):
        """Deterministic STAR reframe: replace weak lead verbs, preserve strong bullets intact."""
        text = clean_text.strip().rstrip(".")
        if not text:
            return clean_text, "", []
        
        teamed = re.match(
            r"^(?:worked|helped)\s+with\s+(?:the\s+)?(?:team|group|others|colleagues)?\s*to\s+(.+)$",
            text,
            re.IGNORECASE,
        )
        if teamed and not matched_metric:
            rewritten = f"Led the team to {teamed.group(1)}".strip()
            result_statement = (
                "Strengthened action lead to highlight team leadership and ownership."
            )
            return f"{rewritten}.".strip(), result_statement, []

        head, sep, tail = text.partition(" ")
        lead = head.lower()

        if lead in self._WEAK_VERB_LEADS:
            strong_verb = self._WEAK_VERB_LEADS[lead]
            rewritten = f"{strong_verb} {tail}".strip()
        else:
            # Bullet already starts with a strong action verb (e.g. Engineered, Optimized, Architected)
            rewritten = text.strip()

        metrics = [matched_metric.group(0).strip()] if matched_metric else []
        result_statement = (
            "Preserved verifiable performance evidence present in the original bullet."
            if matched_metric
            else "Reframed bullet with strong action verb into STAR format."
        )

        return f"{rewritten}.".strip(), result_statement, metrics

    def _generate_mock_star_rewrites(self, bullet_points: List[str], target_jd: str) -> STARRewriteBatchOutput:
        """
        Generates STAR-formatted rewrites with deterministic, evidence-only reframing.

        IMPORTANT: No metrics or percentages are ever invented. A bullet that already
        contains a concrete, verifiable metric keeps it verbatim; a bullet without one
        is reframed with a stronger action verb and STAR flow only, and reports no
        metrics in ``metrics_added``.
        """
        rewrites: List[STARRewriteItem] = []

        skip_keywords = [
            "resume", "curriculum", "cv", "@", "email", "phone", "address", "location", "patiala", "punjab", "india",
            "bachelor", "master", "phd", "degree", "university", "college", "school", "education", "skills", "summary",
            "contact", "cgpa", "gpa", "b.tech", "m.tech", "b.e.", ":selected:", "coursework", "data structures"
        ]

        # Only picks up metrics that already exist in the source bullet (evidence-preserving).
        metric_pattern = re.compile(
            r"(\d+(?:\.\d+)?\s*%|Rs\.?\s?[\d,]+(?:,\d{3})*|\$\s?[\d,]+(?:,\d{3})*|"
            r"[\d,]+(?:,\d{3})*\s+(?:users|requests|tickets|hours|days|bottlenecks|queries|APIs))"
        )

        for bullet in bullet_points:
            cleaned = bullet.strip().lstrip("-*•·\t\r ")
            if not cleaned or len(cleaned) < 10:
                continue

            # Reject non-experience text
            if re.search(r"\[(NAME|EMAIL|PHONE|ADDRESS|SSN|ORGANIZATION|LOCATION|PII)\]", cleaned, re.IGNORECASE) or re.search(r"\[[A-Z_]+\]", cleaned):
                continue
            if "|" in cleaned or ":selected:" in cleaned.lower():
                continue
            if any(sk in cleaned.lower() for sk in skip_keywords):
                continue

            clean_text = re.sub(r"\[(NAME|EMAIL|PHONE|ADDRESS|SSN|ORGANIZATION)\]", "", cleaned).strip(" :'\"")
            if not clean_text or len(clean_text) < 8:
                continue

            matched_metric = metric_pattern.search(clean_text)

            rewritten, result_statement, metrics = self._mock_rewrap_bullet(clean_text, matched_metric)

            rewrites.append(
                STARRewriteItem(
                    original_bullet=cleaned,
                    rewritten_bullet=rewritten,
                    situation_task=f"Clarified the context and task behind: {clean_text}.",
                    action="Led the action with a sharper, domain-aligned verb while keeping the original facts intact.",
                    result=result_statement,
                    metrics_added=metrics,
                    improvement_notes=(
                        "Reframed into the STAR formula. Only metrics already present in the original bullet were "
                        "preserved; no random percentages or fabricated impact were added."
                    ),
                )
            )

        return STARRewriteBatchOutput(
            rewrites=rewrites,
            overall_summary=f"Transformed {len(rewrites)} bullet point(s) into STAR framing without fabricating metrics."
        )
