"""
Module 2: Azure AI Language Service & PII Redaction Engine
Responsible for:
1. PII Detection and Reverse-Offset Masking ([NAME], [EMAIL], [PHONE], etc.)
2. Named Entity Recognition (NER) for Skills and Certifications
3. Offline Regex Fallback for resilient local development and unit testing
"""

import os
import re
import logging
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics import TextAnalyticsClient
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# =====================================================================
# 1. Pydantic Data Contracts (Shared Schemas)
# =====================================================================

class DetectedPII(BaseModel):
    """Schema representing an individual detected PII entity."""
    type: str = Field(description="Category of PII, e.g., 'Person', 'Email', 'PhoneNumber'")
    text: str = Field(description="The actual sensitive text snippet identified")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score from Azure AI")


class RedactPIIResponse(BaseModel):
    """
    Module 2 Output Contract:
    Returned by AILanguageService.redact_pii_and_extract_entities()
    """
    clean_text: str = Field(
        default="", 
        description="Sanitized resume text with sensitive entities masked as [NAME], [EMAIL], etc."
    )
    detected_pii: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="List of detected sensitive entities with metadata"
    )
    extracted_skills: List[str] = Field(
        default_factory=list, 
        description="Distinct technical and professional skills extracted via NER"
    )
    extracted_certifications: List[str] = Field(
        default_factory=list, 
        description="Detected professional certifications"
    )


# =====================================================================
# 2. PII Tag Mapping Configuration
# =====================================================================

PII_TAG_MAP = {
    "Person": "[NAME]",
    "PersonType": "[NAME]",
    "Email": "[EMAIL]",
    "PhoneNumber": "[PHONE]",
    "Address": "[ADDRESS]",
    "USSocialSecurityNumber": "[SSN]",
    "IPAddress": "[IP_ADDRESS]",
    "URL": "[URL]",
    "DateTime": "[DATE]"
}

# =====================================================================
# Pre-compiled Regex Patterns (Day 2 Performance Optimization)
# =====================================================================
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
PHONE_PATTERN = re.compile(r'(?:\+?\d{1,4}[-.\s]?)?(?:\(?\d{2,5}\)?[-.\s]?)?\d{3,5}[-.\s]?\d{3,5}\b')
SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')


# =====================================================================
# 3. Main Service Class
# =====================================================================

class AILanguageService:
    def __init__(self, endpoint: Optional[str] = None, key: Optional[str] = None):
        """
        Initializes the Azure TextAnalyticsClient using environment variables 
        or explicit arguments. Gracefully degrades to offline mock mode if keys are unset.
        """
        load_dotenv()
        self.endpoint = endpoint or os.getenv("AZURE_AI_LANG_ENDPOINT")
        self.key = key or os.getenv("AZURE_AI_LANG_KEY")
        self.client: Optional[TextAnalyticsClient] = None
        self.is_configured: bool = False

        force_offline = os.getenv("FORCE_OFFLINE", "0").lower() in ("true", "1")
        # Validate credentials (reject placeholder values from .env.example)
        if (
            not force_offline
            and self.endpoint 
            and self.key 
            and "your-language-resource" not in self.endpoint 
            and "your_language_key_here" not in self.key
        ):
            try:
                self.client = TextAnalyticsClient(
                    endpoint=self.endpoint, 
                    credential=AzureKeyCredential(self.key),
                    connection_timeout=10,
                    read_timeout=15,
                    retry_total=2,
                )
                self.is_configured = True
                logger.info("Azure AI Language TextAnalyticsClient initialized successfully.")
            except Exception as e:
                logger.warning(f"Failed to initialize Azure AI Language client: {e}. Falling back to offline mode.")
                self.is_configured = False
        else:
            logger.info("No Azure AI Language credentials configured or FORCE_OFFLINE=1. Running in offline/mock mode.")
            self.is_configured = False

    def _sync_redact_and_extract(self, raw_text: str) -> RedactPIIResponse:
        pii_docs = self.client.recognize_pii_entities([raw_text])
        detected_pii: List[Dict[str, Any]] = []
        clean_text = raw_text

        if pii_docs and not pii_docs[0].is_error:
            doc = pii_docs[0]
            sorted_entities = sorted(doc.entities, key=lambda e: e.offset, reverse=True)

            for ent in sorted_entities:
                detected_pii.append({
                    "type": ent.category,
                    "text": ent.text,
                    "confidence": round(ent.confidence_score, 2)
                })
                tag = PII_TAG_MAP.get(ent.category, f"[{ent.category.upper()}]")
                clean_text = clean_text[:ent.offset] + tag + clean_text[ent.offset + ent.length:]

        ner_docs = self.client.recognize_entities([raw_text])
        skills: List[str] = []
        certifications: List[str] = []

        if ner_docs and not ner_docs[0].is_error:
            doc = ner_docs[0]
            for ent in doc.entities:
                if ent.category in ("Skill", "Product"):
                    skills.append(ent.text)
                elif ent.category == "Certification":
                    certifications.append(ent.text)
                elif any(cert_kw in ent.text.lower() for cert_kw in ["certified", "associate", "professional", "pmp", "master"]):
                    certifications.append(ent.text)

        unique_skills = sorted(list({s.strip() for s in skills if s.strip()}))
        unique_certs = sorted(list({c.strip() for c in certifications if c.strip()}))

        return RedactPIIResponse(
            clean_text=clean_text,
            detected_pii=detected_pii,
            extracted_skills=unique_skills,
            extracted_certifications=unique_certs
        )

    async def redact_pii_and_extract_entities(self, raw_text: str) -> RedactPIIResponse:
        """
        Main pipeline method:
        1. Identifies and redacts PII using reverse-offset replacement.
        2. Extracts skills and certifications using NER.
        3. Returns structured RedactPIIResponse.
        """
        if not raw_text or not raw_text.strip():
            return RedactPIIResponse()

        if not self.is_configured or not self.client:
            return self._offline_fallback(raw_text)

        try:
            return await asyncio.to_thread(self._sync_redact_and_extract, raw_text)
        except Exception as e:
            logger.error(f"Error during Azure AI Language execution: {e}. Falling back to offline parser.")
            return self._offline_fallback(raw_text)

    def _offline_fallback(self, raw_text: str) -> RedactPIIResponse:
        """
        Local regex-based fallback for testing without active Azure credentials.
        Optimized on Day 2 with pre-compiled regexes for sub-millisecond execution.
        """
        clean_text = raw_text
        detected_pii: List[Dict[str, Any]] = []

        # 1. Mask Emails using pre-compiled pattern
        for match in EMAIL_PATTERN.finditer(raw_text):
            detected_pii.append({
                "type": "Email",
                "text": match.group(),
                "confidence": 0.99
            })
        clean_text = EMAIL_PATTERN.sub("[EMAIL]", clean_text)

        # 2. Mask Phone Numbers (International & US formats)
        for match in PHONE_PATTERN.finditer(raw_text):
            detected_pii.append({
                "type": "PhoneNumber",
                "text": match.group(),
                "confidence": 0.95
            })
        clean_text = PHONE_PATTERN.sub("[PHONE]", clean_text)

        # 3. Mask SSNs
        for match in SSN_PATTERN.finditer(raw_text):
            detected_pii.append({
                "type": "USSocialSecurityNumber",
                "text": match.group(),
                "confidence": 0.99
            })
        clean_text = SSN_PATTERN.sub("[SSN]", clean_text)

        # 4. Common Skill Dictionary Matching
        common_skills = [
            "Python", "FastAPI", "Docker", "SQL", "Azure", "Git", 
            "React", "JavaScript", "TypeScript", "Machine Learning", 
            "NLP", "PyTorch", "TensorFlow", "Kubernetes", "C++", "Java"
        ]
        extracted_skills = [
            skill for skill in common_skills 
            if re.search(rf"\b{re.escape(skill)}\b", raw_text, re.IGNORECASE)
        ]

        # 5. Common Certification Matching
        common_certs = [
            "AWS Certified", "Azure AI-103", "Azure Fundamentals", 
            "PMP", "Scrum Master", "CKA", "GCP Professional"
        ]
        extracted_certs = [
            cert for cert in common_certs 
            if re.search(rf"\b{re.escape(cert)}\b", raw_text, re.IGNORECASE)
        ]

        return RedactPIIResponse(
            clean_text=clean_text,
            detected_pii=detected_pii,
            extracted_skills=sorted(extracted_skills),
            extracted_certifications=sorted(extracted_certs)
        )

