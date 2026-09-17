"""
Master Orchestrator Pipeline (Resume Doctor Backend).

Connects and executes the async pipeline steps across team services:
1. Member 1: Document Parsing (PDF/DOCX layout & text extraction via Azure Doc Intelligence)
2. Member 2: PII Redaction & Skill Extraction (Azure AI Language)
3. Member 3: ATS Scoring & STAR Bullet Point Rewriting (Azure OpenAI GPT-4o)
4. Member 4: Job Description Matcher (TF-IDF / Cosine Similarity)
"""

import re           # Standard regular expressions module for parsing line text patterns
from typing import Dict, Any  # Type hinting annotations for dictionaries

# Import Member 1 Document Intelligence Service
from src.backend.services.doc_intelligence import DocIntelligenceService
# Import Member 3 Azure OpenAI Service
from src.backend.services.azure_openai import AzureOpenAIService


class MasterOrchestrator:
    """
    Master Orchestrator class responsible for sequencing multi-service async processing.
    """
    def __init__(self):
        # Initialize Member 1 Service (Azure AI Document Intelligence)
        self.doc_service = DocIntelligenceService()
        
        # Initialize Member 3 Service (Azure OpenAI GPT-4o ATS Scoring & STAR Rewrite Engine)
        self.openai_service = AzureOpenAIService()

    async def process_resume_pipeline(
        self, file_bytes: bytes, file_name: str, target_jd: str = ""
    ) -> Dict[str, Any]:
        """
        Master Async Pipeline Execution Method:
        Takes resume file bytes and optional Job Description text, executing end-to-end audit.
        """
        # Step 1: Document Parsing (Member 1 - Document Intelligence)
        parsed_doc = self.doc_service.parse_resume(file_bytes, file_name)
        
        # Extract plain text string from parsed document payload
        extracted_text = (
            parsed_doc.get("extracted_text", "")
            if isinstance(parsed_doc, dict)
            else str(parsed_doc)
        )

        # Step 3: ATS Scoring Audit (Member 3 - Azure OpenAI GPT-4o)
        ats_score_result = await self.openai_service.async_analyze_ats(
            extracted_text, target_jd
        )

        # Extract candidate bullet points from resume text for STAR rewriting
        lines = [line.strip(" -*•\t\r") for line in extracted_text.split("\n") if line.strip()]
        
        # Filter out headers, contact emails, addresses, titles to isolate bullet statements
        candidate_bullets = []
        for line in lines:
            line_lower = line.lower()
            if (
                len(line) > 20  # Minimum line length requirement for a meaningful bullet statement
                and "@" not in line  # Exclude email addresses
                and not any(header in line_lower for header in ["resume", "curriculum vitae", "contact", "summary", "education", "experience", "skills", "references"]) # Exclude section headers
                and not re.search(r"\d{5}", line)  # Exclude zip codes / address lines
            ):
                candidate_bullets.append(line)  # Keep valid bullet statement
                if len(candidate_bullets) >= 5: # Limit batch to top 5 candidates
                    break

        # Fallback bullet if no candidate lines were detected in parsed text
        if not candidate_bullets:
            candidate_bullets = ["Built a website."]

        # Step 3 (Continued): STAR Bullet Point Rewriting (Member 3 - Azure OpenAI GPT-4o)
        star_rewrites_result = await self.openai_service.async_rewrite_star_bullets(
            candidate_bullets, target_jd
        )

        # Assemble and return consolidated master pipeline response object
        return {
            "parsed_document": parsed_doc,
            "ats_scoring": ats_score_result.model_dump(),             # Convert Pydantic ATS model to dict
            "star_bullet_rewrites": star_rewrites_result.model_dump(), # Convert Pydantic STAR model to dict
            "pipeline_status": "Step 1 (Doc Intel) & Step 3 (Azure OpenAI ATS) Complete",
        }
