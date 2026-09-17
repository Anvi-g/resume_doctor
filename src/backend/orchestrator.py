"""
Master Orchestrator Pipeline (Resume Doctor Backend).

Connects and executes the async pipeline steps across team services:
1. Member 1: Document Parsing (PDF/DOCX layout & text extraction via Azure Doc Intelligence)
2. Member 2: PII Redaction & Skill Extraction (Azure AI Language)
3. Member 3: ATS Scoring & STAR Bullet Point Rewriting (Azure OpenAI GPT-4o)
4. Member 4: Job Description Matcher (TF-IDF / Cosine Similarity)

Executes Member 3 (ATS / STAR) and Member 4 (JD Matcher) concurrently via asyncio.gather().
"""

import re
import time
import asyncio
import logging
from typing import Dict, Any, Optional, List

# Import Member 1 Document Intelligence Service
from src.backend.services.doc_intelligence import DocIntelligenceService
# Import Member 2 Azure AI Language Service
from src.backend.services.ai_language import AILanguageService
# Import Member 3 Azure OpenAI Service
from src.backend.services.azure_openai import AzureOpenAIService
# Import Member 4 JD Matcher Service
from src.backend.services.jd_matcher import JDMatcherService
# Import Shared Schemas
from src.backend.models.schemas import (
    MasterAnalyzeResponse,
    JDMatchResult,
    ParseResumeResponse,
    RedactPIIResponse,
    ATSScoreOutput,
    STARRewriteBatchOutput,
)

logger = logging.getLogger(__name__)


class MasterOrchestrator:
    """
    Master Orchestrator class responsible for sequencing multi-service async processing.
    Features concurrent execution of ATS Scoring (M3) and JD Matcher (M4) via asyncio.gather().
    """
    def __init__(self):
        # Initialize Member 1 Service (Azure AI Document Intelligence)
        self.doc_service = DocIntelligenceService()
        
        # Initialize Member 2 Service (Azure AI Language PII & NER)
        self.language_service = AILanguageService()

        # Initialize Member 3 Service (Azure OpenAI GPT-4o ATS Scoring & STAR Rewrite Engine)
        self.openai_service = AzureOpenAIService()

        # Initialize Member 4 Service (TF-IDF JD Matcher)
        self.jd_matcher = JDMatcherService()

    async def process_resume_pipeline(
        self,
        file_bytes: bytes,
        file_name: str = "resume.pdf",
        target_jd: str = "",
        filename: Optional[str] = None,
        job_description: Optional[str] = None,
        target_role: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Master Async Pipeline Execution Method:
        1. Member 1: Parse layout & raw text
        2. Member 2: Redact sensitive PII & extract technical skills
        3. Concurrently (asyncio.gather):
           - Member 3: Azure OpenAI ATS score & STAR bullet rewrites
           - Member 4: TF-IDF Cosine Similarity & Skill Gap Analysis
        """
        actual_filename = filename or file_name or "resume.pdf"
        actual_jd = job_description if job_description is not None else target_jd

        # -------------------------------------------------------------
        # Step 1: Member 1 - Document Parsing (Azure Doc Intel / Fallback)
        # -------------------------------------------------------------
        parsed_doc = self.doc_service.parse_resume(file_bytes, actual_filename)
        extracted_text = (
            parsed_doc.get("extracted_text", "")
            or parsed_doc.get("raw_text", "")
            if isinstance(parsed_doc, dict)
            else str(parsed_doc)
        )

        # -------------------------------------------------------------
        # Step 2: Member 2 - PII Redaction & Skill Extraction
        # -------------------------------------------------------------
        pii_res = await self.language_service.redact_pii_and_extract_entities(extracted_text)
        clean_text = pii_res.clean_text if pii_res and pii_res.clean_text else extracted_text
        resume_skills = pii_res.extracted_skills if pii_res else []

        # -------------------------------------------------------------
        # Step 3 & 4: CONCURRENT EXECUTION (Member 3 & Member 4)
        # Running via asyncio.gather() cuts total latency significantly
        # -------------------------------------------------------------
        lines = [line.strip(" -*•\t\r") for line in clean_text.split("\n") if line.strip()]
        candidate_bullets: List[str] = []
        for line in lines:
            line_lower = line.lower()
            if (
                len(line) > 20
                and "@" not in line
                and not any(header in line_lower for header in ["resume", "curriculum vitae", "contact", "summary", "education", "experience", "skills", "references"])
                and not re.search(r"\d{5}", line)
            ):
                candidate_bullets.append(line)
                if len(candidate_bullets) >= 5:
                    break

        if not candidate_bullets:
            candidate_bullets = ["Built and maintained scalable application software."]

        # Define M3 task (ATS Score + STAR Rewrites)
        async def _run_member_3():
            ats_task = self.openai_service.async_analyze_ats(clean_text, actual_jd)
            star_task = self.openai_service.async_rewrite_star_bullets(candidate_bullets, actual_jd)
            return await asyncio.gather(ats_task, star_task)

        # Define M4 task (JD Matcher)
        async def _run_member_4():
            return self.jd_matcher.match(clean_text, actual_jd, resume_skills)

        # Execute Member 3 and Member 4 concurrently using asyncio.gather()
        (m3_results, jd_match) = await asyncio.gather(_run_member_3(), _run_member_4())
        ats_score_result, star_rewrites_result = m3_results

        ats_dict = ats_score_result.model_dump() if hasattr(ats_score_result, "model_dump") else ats_score_result
        star_dict = star_rewrites_result.model_dump() if hasattr(star_rewrites_result, "model_dump") else star_rewrites_result
        jd_dict = jd_match.model_dump() if hasattr(jd_match, "model_dump") else jd_match
        pii_dict = pii_res.model_dump() if hasattr(pii_res, "model_dump") else pii_res

        status = (
            "Step 1 (Doc Intelligence) Ready"
            if not actual_jd
            else "Step 1 (Doc Intel), Step 2 (PII/NER), Step 3 (Azure OpenAI ATS), and Step 4 (JD Matcher) Complete"
        )

        # Return consolidated dictionary satisfying Member 1, 2, 3, and 4
        return {
            "parsed_document": parsed_doc,
            "doc_summary": parsed_doc,
            "pii_summary": pii_dict,
            "ats_scoring": ats_dict,
            "ats_analysis": ats_dict,
            "star_bullet_rewrites": star_dict,
            "jd_match": jd_dict,
            "pipeline_status": status,
        }

    async def analyze_to_model(
        self,
        file_bytes: bytes,
        filename: str = "resume.pdf",
        job_description: str = "",
        target_role: str = ""
    ) -> MasterAnalyzeResponse:
        """Helper that returns the strict MasterAnalyzeResponse schema for /api/analyze."""
        raw_res = await self.process_resume_pipeline(
            file_bytes=file_bytes,
            filename=filename,
            job_description=job_description,
            target_role=target_role
        )
        return MasterAnalyzeResponse(
            doc_summary=raw_res.get("parsed_document", {}),
            pii_summary=raw_res.get("pii_summary", {}),
            ats_analysis=raw_res.get("ats_scoring", {}),
            jd_match=JDMatchResult(**raw_res.get("jd_match", {}))
        )
