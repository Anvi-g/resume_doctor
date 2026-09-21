"""
Data Models and Pydantic Schemas for Resume Doctor Backend.

This module defines all structured data models for:
1. ATS Score Category Breakdown
2. Overall ATS Evaluation Output Schema
3. Individual STAR Bullet Point Transformation Schema
4. Batch STAR Bullet Point Transformation Output Schema
5. FastAPI HTTP Request payloads for ATS Scoring and STAR Rewrites
"""

from typing import List, Optional, Dict, Any
# Import BaseModel and Field from Pydantic for data validation and OpenAPI schema generation
from pydantic import BaseModel, Field


class ATSCategoryBreakdown(BaseModel):
    """
    Represents the breakdown of scores across the 5 core ATS audit categories.
    Total score cap across all categories sums to 100 marks.
    """
    # Formatting score: Validates clean section headings, standard fonts, and email/phone format (0-20 marks)
    formatting_score: int = Field(
        default=0, ge=0, le=20, description="Formatting & Structure score (0-20 marks)"
    )
    # Keyword score: Measures presence of required technical skills and domain keywords (0-25 marks)
    keywords_score: int = Field(
        default=0, ge=0, le=25, description="Keyword Optimization score (0-25 marks)"
    )
    # Section score: Evaluates inclusion of mandatory sections like Summary, Experience, Education, Skills (0-15 marks)
    sections_score: int = Field(
        default=0, ge=0, le=15, description="Section Completeness score (0-15 marks)"
    )
    # Action verbs score: Assesses usage of strong dynamic action verbs (0-20 marks)
    action_verbs_score: int = Field(
        default=0, ge=0, le=20, description="Action Verbs usage score (0-20 marks)"
    )
    # Impact score: Evaluates presence of quantifiable business metrics, percentages, and scale (0-20 marks)
    impact_score: int = Field(
        default=0, ge=0, le=20, description="Impact & Metrics score (0-20 marks)"
    )


class ATSScoreOutput(BaseModel):
    """
    Complete ATS Evaluation Output Schema returned by Azure OpenAI GPT-4o structured LLM chain.
    """
    # Arithmetic sum of all 5 category scores (0-100 marks)
    overall_score: int = Field(
        ..., ge=0, le=100, description="Overall aggregated ATS score out of 100"
    )
    # Individual category scores for fast frontend rendering
    formatting_score: int = Field(..., ge=0, le=20, description="Formatting score out of 20")
    keywords_score: int = Field(..., ge=0, le=25, description="Keyword score out of 25")
    sections_score: int = Field(..., ge=0, le=15, description="Section completeness score out of 15")
    action_verbs_score: int = Field(..., ge=0, le=20, description="Action verb usage score out of 20")
    impact_score: int = Field(..., ge=0, le=20, description="Impact & metrics score out of 20")
    
    # Executive summary providing human-readable overall feedback on resume quality
    summary_feedback: str = Field(..., description="High-level narrative feedback summary")
    
    # List of key strengths detected in the resume text
    strengths: List[str] = Field(
        default_factory=list, description="List of key resume strengths identified by ATS"
    )
    # List of concrete recommendations to improve ATS compatibility and ranking
    improvements: List[str] = Field(
        default_factory=list, description="Actionable recommendations for resume improvement"
    )
    # List of critical technical/domain keywords missing relative to role requirements
    missing_keywords: List[str] = Field(
        default_factory=list, description="Important role/industry keywords missing from resume"
    )


class STARRewriteItem(BaseModel):
    """
    Represents an individual bullet point rewritten into the STAR (Situation, Task, Action, Result) format.
    """
    # The original unoptimized bullet point submitted by the user
    original_bullet: str = Field(..., description="The original bullet point provided by user")
    
    # The enhanced STAR bullet point featuring strong action verbs, context, and metrics
    rewritten_bullet: str = Field(..., description="The rewritten bullet in metric-driven STAR format")
    
    # Context or challenge statement explaining the Situation/Task component
    situation_task: Optional[str] = Field(
        None, description="Context, situation, or challenge addressed in bullet"
    )
    # Specific action taken, including technologies, frameworks, and technical strategies used
    action: Optional[str] = Field(
        None, description="Specific tech stack and action taken"
    )
    # Quantifiable outcome, business value, or latency/efficiency improvement achieved
    result: Optional[str] = Field(
        None, description="Quantifiable outcome or business impact achieved"
    )
    # List of specific metrics or percentages incorporated into the rewrite
    metrics_added: List[str] = Field(
        default_factory=list, description="Metrics or percentages added to bullet point"
    )
    # Concise explanation explaining why this rewrite improves ATS optimization
    improvement_notes: str = Field(
        ..., description="Explanation of why the rewrite improves ATS rating"
    )


class STARRewriteBatchOutput(BaseModel):
    """
    Batch Output Schema containing rewrites for multiple resume bullet points.
    """
    # Collection of rewritten STAR bullet items
    rewrites: List[STARRewriteItem] = Field(
        ..., description="List of rewritten STAR bullet items"
    )
    # High-level summary describing the enhancements applied across the bullet points
    overall_summary: str = Field(
        ..., description="Executive summary of bullet enhancements applied"
    )


# ==========================================
# FastAPI HTTP Request Payload Schemas
# ==========================================

class ATSScoreRequest(BaseModel):
    """
    Request schema for POST /api/ats/score endpoint.
    """
    # The raw parsed text content of the candidate's resume
    resume_text: str = Field(..., description="Parsed raw text of the resume")
    # Optional Job Description text to evaluate keyword alignment against specific job postings
    target_jd: Optional[str] = Field(
        "", description="Optional Job Description text for targeted evaluation"
    )


class STARRewriteRequest(BaseModel):
    """
    Request schema for POST /api/ats/star-rewrite endpoint.
    """
    # Array of unoptimized bullet points to be transformed into STAR format
    bullet_points: List[str] = Field(
        ..., description="List of bullet points to rewrite into STAR format"
    )
    # Optional Job Description context to tailor technical action verbs to target roles
    target_jd: Optional[str] = Field(
        "", description="Optional Job Description text for targeted rewriting"
    )


# =====================================================================
# Member 4 (Data Lead) Schemas & Master Gateway Response Contracts
# Reference: Resume Doctor Master Project Plan (Page 2 & 3)
# =====================================================================

class ParseResumeResponse(BaseModel):
    """Module 1 Output Schema."""
    raw_text: str = Field(default="", description="Extracted resume text")
    page_count: int = Field(default=1, description="Total pages parsed")
    tables: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted table structures")
    file_type: str = Field(default="pdf", description="File extension ('pdf' | 'docx')")


class RedactPIIResponse(BaseModel):
    """Module 2 Output Schema."""
    clean_text: str = Field(default="", description="Sanitized resume text with sensitive entities masked")
    detected_pii: List[Dict[str, Any]] = Field(default_factory=list, description="Detected sensitive entities")
    extracted_skills: List[str] = Field(default_factory=list, description="Extracted technical/professional skills")
    extracted_certifications: List[str] = Field(default_factory=list, description="Extracted certifications")


class StarRewrite(BaseModel):
    """Module 3 Compact STAR Rewrite."""
    original: str = Field(..., description="Original weak bullet point")
    improved_star: str = Field(..., description="Rewritten bullet in STAR format")
    impact_metric: str = Field(..., description="Measurable metric added to bullet")


class ATSAnalysisResult(BaseModel):
    """Module 3 Output Schema."""
    ats_score: int = Field(..., ge=0, le=100, description="Overall ATS score (0-100)")
    strengths: List[str] = Field(default_factory=list, description="Key strengths identified")
    weaknesses: List[str] = Field(default_factory=list, description="Identified areas for improvement")
    star_rewrites: List[StarRewrite] = Field(default_factory=list, description="STAR bullet transformations")
    format_issues: List[str] = Field(default_factory=list, description="Format warnings")


class JDMatchResult(BaseModel):
    """Module 4 Output Schema."""
    match_percentage: float = Field(..., ge=0.0, le=100.0, description="Match percentage (0.0 to 100.0%)")
    matched_skills: List[str] = Field(default_factory=list, description="Skills present in both JD and Resume")
    missing_skills: List[str] = Field(default_factory=list, description="Required JD skills absent from Resume")
    recommendations: List[str] = Field(default_factory=list, description="Actionable recommendations to bridge gap")
    cosine_similarity: float = Field(default=0.0, ge=0.0, le=1.0, description="TF-IDF cosine similarity score")
    skill_match_ratio: float = Field(default=0.0, ge=0.0, le=1.0, description="Ratio of matched skills to required skills")


class MasterAnalyzeResponse(BaseModel):
    """Master Gateway Response Schema for POST /api/analyze."""
    doc_summary: Any = Field(..., description="Member 1 document summary or dict")
    pii_summary: Any = Field(..., description="Member 2 PII summary or dict")
    ats_analysis: Any = Field(..., description="Member 3 ATS evaluation or dict")
    jd_match: JDMatchResult = Field(..., description="Member 4 JD matching result")

    def __getitem__(self, item: str):
        return getattr(self, item)

    def __contains__(self, item: str):
        return hasattr(self, item)


class DirectJDMatchRequest(BaseModel):
    """Request payload for direct testing of JD Matcher endpoint."""
    clean_text: str
    jd_text: str
    resume_skills: List[str] = Field(default_factory=list)

