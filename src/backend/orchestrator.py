"""
Master Orchestrator Pipeline (Resume Doctor Backend).

Connects and executes the async pipeline steps across team services:
1. Member 1: Document Parsing (PDF/DOCX layout & text extraction via Azure Doc Intelligence)
2. Member 2: PII Redaction & Skill Extraction (Azure AI Language)
3. Member 3: ATS Scoring & STAR Bullet Point Rewriting (Azure OpenAI GPT-4o)
4. Member 4: Job Description Matcher (TF-IDF / Cosine Similarity)
"""

import re
import logging
from typing import Dict, Any

# Import Member 1 Document Intelligence Service
from src.backend.services.doc_intelligence import DocIntelligenceService
# Import Member 3 Azure OpenAI Service
from src.backend.services.azure_openai import AzureOpenAIService

logger = logging.getLogger(__name__)


class MasterOrchestrator:
    """
    Member 1 & Team Master Orchestration Engine
    Coordinates end-to-end execution across all Azure AI backend modules.
    """
    def __init__(self):
        # Member 1: Azure AI Document Intelligence Service
        self.doc_service = DocIntelligenceService()
        
        # Member 2: Azure AI Language PII & NER Engine (placeholder)
        self.ai_lang_service = None
        
        # Member 3: Azure OpenAI GPT-4o ATS Scoring & STAR Rewrite Engine
        self.openai_service = AzureOpenAIService()
        
        # Member 4: Job Description Matcher (placeholder)
        self.jd_matcher_service = None

    async def process_resume_pipeline(
        self, file_bytes: bytes, file_name: str, target_jd: str = ""
    ) -> Dict[str, Any]:
        """
        Master Async Pipeline Execution Method:
        Takes resume file bytes and optional Job Description text, executing end-to-end audit.
        """
        # --- Stage 1: Document Intelligence Parsing (Member 1) ---
        parsed_doc = self.doc_service.parse_resume(file_bytes, file_name)
        
        # Extract plain text string from parsed document payload
        raw_text = ""
        if isinstance(parsed_doc, dict):
            raw_text = parsed_doc.get("raw_text", "") or parsed_doc.get("extracted_text", "")
        else:
            raw_text = str(parsed_doc)

        # --- Stage 3: ATS Scoring & STAR Rewrites (Member 3 - Azure OpenAI) ---
        ats_score_result = None
        star_rewrites_result = None
        
        if self.openai_service:
            try:
                ats_score_result = await self.openai_service.async_analyze_ats(
                    raw_text, target_jd
                )

                # Extract candidate bullet points from resume text for STAR rewriting
                lines = [line.strip(" -*•\t\r") for line in raw_text.split("\n") if line.strip()]
                
                # Filter out headers, contact emails, addresses, titles to isolate bullet statements
                candidate_bullets = []
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
                    candidate_bullets = ["Built a website."]

                star_rewrites_result = await self.openai_service.async_rewrite_star_bullets(
                    candidate_bullets, target_jd
                )
            except Exception as e:
                logger.warning(f"Azure OpenAI pipeline step skipped: {e}")

        ats_dump = ats_score_result.model_dump() if ats_score_result else None
        star_dump = star_rewrites_result.model_dump() if star_rewrites_result else None

        # Assembled Master Pipeline Response Object
        response = {
            "document_metadata": {
                "file_name": file_name,
                "file_type": parsed_doc.get("file_type") if isinstance(parsed_doc, dict) else "pdf",
                "page_count": parsed_doc.get("page_count", 1) if isinstance(parsed_doc, dict) else 1,
                "parsing_mode": parsed_doc.get("mode") if isinstance(parsed_doc, dict) else "local_fallback"
            },
            "parsed_content": {
                "raw_text": raw_text,
                "sections": parsed_doc.get("sections", {}) if isinstance(parsed_doc, dict) else {},
                "tables": parsed_doc.get("tables", []) if isinstance(parsed_doc, dict) else []
            },
            "parsed_document": parsed_doc,
            "privacy_nlp": None,
            "ats_analysis": ats_dump,
            "ats_scoring": ats_dump,
            "star_bullet_rewrites": star_dump,
            "jd_match_results": None,
            "pipeline_stages": {
                "stage_1_doc_intel": True,
                "stage_2_pii_nlp": False,
                "stage_3_genai_ats": bool(ats_dump),
                "stage_4_jd_matcher": False
            },
            "pipeline_status": "Step 1 (Doc Intel) & Step 3 (Azure OpenAI ATS) Complete" if ats_dump else "Step 1 Complete - Document Layout Parsed",
            "status": "Stage 3 Complete - GenAI ATS Evaluated" if ats_dump else "Stage 1 Complete - Document Layout Parsed"
        }

        return response
