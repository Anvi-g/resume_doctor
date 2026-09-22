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
import logging          # Standard library logging module for recording events and errors
import asyncio          # Standard library asyncio module for asynchronous event loop operations
from typing import List, Optional, Dict, Any  # Type hinting annotations
from dotenv import load_dotenv               # Load environment variables from .env file


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
        request_timeout: int = 30,              # API HTTP request timeout in seconds
        max_retries: int = 2,                   # Number of automated retry attempts on failure
    ):
        # Resolve endpoint from argument if passed, else environment variable AZURE_OPENAI_ENDPOINT
        self.endpoint = endpoint if endpoint is not None else os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
        
        # Resolve API key from argument if passed, else environment variable AZURE_OPENAI_KEY
        self.api_key = api_key if api_key is not None else os.getenv("AZURE_OPENAI_KEY", "").strip()
        
        # Resolve deployment name (default to gpt-4o)
        self.deployment_name = (
            deployment_name
            or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o").strip()
        )
        
        # Resolve API version (default to 2024-02-15-preview)
        self.api_version = (
            api_version
            or os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview").strip()
        )
        
        self.temperature = temperature      # Store temperature setting
        self.request_timeout = request_timeout # Store timeout setting
        self.max_retries = max_retries      # Store max retries setting

        # Determine if offline mock mode should be enabled (force_mock flag or missing/placeholder credentials)
        force_mock = os.getenv("MOCK_AZURE_OPENAI", "false").lower() in ("true", "1")
        has_credentials = (
            bool(self.endpoint)
            and bool(self.api_key)
            and "your_" not in self.api_key.lower()
            and "<your-" not in self.endpoint.lower()
        )
        self.is_mock_mode = force_mock or not has_credentials

        self.llm = None  # Holds AzureChatOpenAI instance
        if not self.is_mock_mode:
            try:
                # Instantiate AzureChatOpenAI client using LangChain
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
                # Log warning and switch to mock mode on initialization error
                logger.warning(f"Failed to initialize AzureChatOpenAI client ({e}). Switching to fallback mode.")
                self.is_mock_mode = True
        else:
            logger.info("AzureOpenAIService running in Mock / Offline mode.")

    def analyze_ats(self, resume_text: str, target_jd: str = "") -> ATSScoreOutput:
        """
        Synchronous ATS scoring analysis method.
        """
        # Return deterministic mock response if mock mode is active or LLM is uninitialized
        if self.is_mock_mode or not self.llm:
            return self._generate_mock_ats_score(resume_text, target_jd)

        try:
            # Bind structured Pydantic output model ATSScoreOutput to the LLM
            structured_llm = self.llm.with_structured_output(ATSScoreOutput)
            # Combine prompt template and structured LLM using LangChain Runnable Sequence (pipe operator)
            chain = ATS_SCORING_PROMPT_TEMPLATE | structured_llm
            # Execute chain synchronously with input variables
            result: ATSScoreOutput = chain.invoke({
                "resume_text": resume_text,
                "target_jd": target_jd or "General Technical Role",
            })
            return result
        except Exception as e:
            # Catch API errors, log exception, and fallback gracefully
            logger.error(f"Error during Azure OpenAI ATS scoring invocation: {e}")
            return self._generate_mock_ats_score(resume_text, target_jd)

    async def async_analyze_ats(self, resume_text: str, target_jd: str = "") -> ATSScoreOutput:
        """
        Asynchronous ATS scoring analysis method for FastAPI async route execution.
        """
        # Return deterministic mock response if mock mode is active
        if self.is_mock_mode or not self.llm:
            return self._generate_mock_ats_score(resume_text, target_jd)

        try:
            # Bind structured output model ATSScoreOutput
            structured_llm = self.llm.with_structured_output(ATSScoreOutput)
            # Create LangChain Runnable Sequence
            chain = ATS_SCORING_PROMPT_TEMPLATE | structured_llm
            # Execute chain asynchronously using ainvoke
            result: ATSScoreOutput = await chain.ainvoke({
                "resume_text": resume_text,
                "target_jd": target_jd or "General Technical Role",
            })
            return result
        except Exception as e:
            logger.error(f"Error during async Azure OpenAI ATS scoring invocation: {e}")
            return self._generate_mock_ats_score(resume_text, target_jd)

    def rewrite_star_bullets(
        self, bullet_points: List[str], target_jd: str = ""
    ) -> STARRewriteBatchOutput:
        """
        Synchronous STAR bullet point rewriting method.
        """
        # Guard clause for empty bullet list
        if not bullet_points:
            return STARRewriteBatchOutput(
                rewrites=[],
                overall_summary="No bullet points were provided for rewriting."
            )

        # Return mock rewrites if mock mode is enabled
        if self.is_mock_mode or not self.llm:
            return self._generate_mock_star_rewrites(bullet_points, target_jd)

        try:
            # Format list of bullets into newline-delimited text
            bullet_text = "\n".join([f"- {b}" for b in bullet_points])
            # Bind structured Pydantic model STARRewriteBatchOutput
            structured_llm = self.llm.with_structured_output(STARRewriteBatchOutput)
            # Create LangChain Runnable Sequence
            chain = STAR_REWRITE_PROMPT_TEMPLATE | structured_llm
            # Execute chain synchronously
            result: STARRewriteBatchOutput = chain.invoke({
                "bullet_points_text": bullet_text,
                "target_jd": target_jd or "General Technical Role",
            })
            return result
        except Exception as e:
            logger.error(f"Error during Azure OpenAI STAR rewrite invocation: {e}")
            return self._generate_mock_star_rewrites(bullet_points, target_jd)

    async def async_rewrite_star_bullets(
        self, bullet_points: List[str], target_jd: str = ""
    ) -> STARRewriteBatchOutput:
        """
        Asynchronous STAR bullet point rewriting method for FastAPI async route execution.
        """
        if not bullet_points:
            return STARRewriteBatchOutput(
                rewrites=[],
                overall_summary="No bullet points were provided for rewriting."
            )

        if self.is_mock_mode or not self.llm:
            return self._generate_mock_star_rewrites(bullet_points, target_jd)

        try:
            # Format bullets into string
            bullet_text = "\n".join([f"- {b}" for b in bullet_points])
            # Bind structured model
            structured_llm = self.llm.with_structured_output(STARRewriteBatchOutput)
            # Create sequence
            chain = STAR_REWRITE_PROMPT_TEMPLATE | structured_llm
            # Execute chain asynchronously
            result: STARRewriteBatchOutput = await chain.ainvoke({
                "bullet_points_text": bullet_text,
                "target_jd": target_jd or "General Technical Role",
            })
            return result
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

        # Heuristic scoring based on resume text properties
        formatting_score = 16 if word_count > 50 else 10
        keywords_score = 20 if any(kw in text_lower for kw in ["python", "azure", "api", "fastapi", "react", "sql", "aws", "docker"]) else 12
        sections_score = 14 if any(sec in text_lower for sec in ["experience", "education", "skills", "projects"]) else 8
        action_verbs_score = 17 if any(v in text_lower for v in ["developed", "built", "implemented", "managed", "designed", "created", "led", "automated"]) else 11
        impact_score = 16 if any(char in text_lower for char in ["%", "$", "reduced", "increased", "supported", "improved", "users"]) else 9

        # Calculate exact total overall score out of 100
        overall_score = min(100, max(0, formatting_score + keywords_score + sections_score + action_verbs_score + impact_score))

        # Return validated ATSScoreOutput Pydantic object
        return ATSScoreOutput(
            overall_score=overall_score,
            formatting_score=formatting_score,
            keywords_score=keywords_score,
            sections_score=sections_score,
            action_verbs_score=action_verbs_score,
            impact_score=impact_score,
            summary_feedback="Resume displays solid technical foundations. Focus on enhancing quantifiable impact metrics and section alignment for top ATS ranking.",
            strengths=[
                "Clear structure with identifiable experience and technical sections.",
                "Good utilization of technical skill terminology."
            ],
            improvements=[
                "Incorporate more specific percentage metrics and revenue impact numbers.",
                "Use strong dynamic action verbs (e.g., 'Spearheaded', 'Engineered') at the start of each bullet point."
            ],
            missing_keywords=["CI/CD", "Kubernetes", "Azure OpenAI", "Microservices Architecture"]
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

    @staticmethod
    def _pick_action_verb(text_lower: str) -> str:
        if any(k in text_lower for k in ("ml", "inference", "model", "prediction", "vision", "nlp", " ai")):
            return "Optimized"
        if any(k in text_lower for k in ("api", "backend", "endpoint", "fastapi", "microservice", "service")):
            return "Architected"
        if any(k in text_lower for k in ("pipeline", "data", "parquet", "csv", "storage", "database", "sql", "etl", "batch")):
            return "Engineered"
        if any(k in text_lower for k in ("automate", "script", "bash", "deploy", "ci/", "workflow")):
            return "Automated"
        if any(k in text_lower for k in ("edge", "security", "biometric", "device", "embedded")):
            return "Designed"
        return "Spearheaded"

    @staticmethod
    def _outcome_clause(text_lower: str) -> str:
        if any(k in text_lower for k in ("pipeline", "data", "parquet", "csv", "storage", "database", "sql", "etl")):
            return "keeping downstream systems query-ready and reliable"
        if any(k in text_lower for k in ("api", "backend", "endpoint", "fastapi", "microservice", "service")):
            return "keeping client workflows fast and dependable"
        if any(k in text_lower for k in ("ml", "inference", "model", "prediction", " ai")):
            return "keeping model outputs consistent and production-tuned"
        if any(k in text_lower for k in ("automate", "script", "bash", "deploy", "ci/", "workflow")):
            return "removing repetitive manual steps from the delivery loop"
        if any(k in text_lower for k in ("edge", "security", "biometric", "device", "embedded")):
            return "with reliability and privacy preserved"
        return ""

    def _mock_rewrap_bullet(self, clean_text: str, matched_metric: Any):
        """Deterministic STAR reframe: replace the lead verb, never invent metrics."""
        text = clean_text.strip().rstrip(".")
        if not text:
            return clean_text, "", []
        lower = text.lower()
        action_verb = self._pick_action_verb(lower)

        teamed = re.match(
            r"^(?:worked|helped)\s+with\s+(?:the\s+)?(?:team|group|others|colleagues)?\s*to\s+(.+)$",
            text,
            re.IGNORECASE,
        )
        if teamed and not matched_metric:
            rewritten = f"Led the team to {teamed.group(1)}".strip()
            clause = self._outcome_clause(lower)
            if clause:
                rewritten = f"{rewritten}, {clause}."
            else:
                rewritten = f"{rewritten}."
            result_statement = (
                "Strengthened the action lead and result framing without introducing any unverifiable numbers."
            )
            return rewritten, result_statement, []

        head, sep, tail = text.partition(" ")
        if sep:
            lead = head.lower()
            if lead in self._WEAK_VERB_LEADS:
                rewritten = f"{self._WEAK_VERB_LEADS[lead]} {tail}"
            else:
                rewritten = f"{action_verb} {head[0].lower() if head else ''}{head[1:]} {tail}"
        else:
            rewritten = f"{action_verb} {head.lower()}"

        if matched_metric:
            metrics = [matched_metric.group(0).strip()]
            result_statement = (
                "Preserved the concrete, verifiable performance evidence present in the original bullet verbatim."
            )
            return f"{rewritten}.".strip(), result_statement, metrics

        clause = self._outcome_clause(lower)
        if clause:
            rewritten = f"{rewritten}, {clause}."
        else:
            rewritten = f"{rewritten}."
        result_statement = (
            "Strengthened the action lead and result framing without introducing any unverifiable numbers."
        )
        return rewritten, result_statement, []

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
