"""
FastAPI Application Gateway for Resume Doctor (Azure AI-103).

Exposes REST HTTP API Endpoints for:
1. GET /health - Server health and GenAI mock mode status check.
2. POST /api/ats/score - Direct ATS scoring evaluation of raw resume text.
3. POST /api/ats/star-rewrite - STAR bullet point transformation engine.
4. POST /api/pipeline/process - Upload resume file (PDF/DOCX) and run full pipeline.
"""

from fastapi import FastAPI, File, UploadFile, Form, HTTPException # FastAPI router and HTTP utilities
from fastapi.middleware.cors import CORSMiddleware                # CORS middleware for cross-origin frontend requests
from typing import Optional                                      # Optional type annotation

# Import Pydantic schemas for request validation and response model specification
from src.backend.models.schemas import (
    ATSScoreRequest,         # Request payload schema for ATS scoring
    ATSScoreOutput,          # Response schema for ATS scoring output
    STARRewriteRequest,      # Request payload schema for STAR rewriting
    STARRewriteBatchOutput,  # Response schema for STAR rewriting batch output
)

# Import Member 3 Azure OpenAI Service
from src.backend.services.azure_openai import AzureOpenAIService
# Import Master Orchestrator Pipeline
from src.backend.orchestrator import MasterOrchestrator

# Initialize FastAPI Application Gateway instance
app = FastAPI(
    title="Resume Doctor API Gateway",
    description="Azure AI-103 Powered Resume Auditing & Optimization Gateway",
    version="1.0.0",
)

# Configure CORS Middleware to allow requests from React Frontend (ports 3000, 5173, etc.)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Allow all origins for local development
    allow_credentials=True,    # Allow cookies and credential headers
    allow_methods=["*"],        # Allow all HTTP verbs (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],        # Allow all HTTP headers
)

# Instantiate singleton service instances
openai_service = AzureOpenAIService()
orchestrator = MasterOrchestrator()


@app.get("/health")
def health_check():
    """
    Health check endpoint returning server status and GenAI mock mode status.
    """
    return {
        "status": "healthy",
        "service": "Resume Doctor API",
        "genai_mock_mode": openai_service.is_mock_mode,  # True if running in offline mock fallback mode
    }


@app.post("/api/ats/score", response_model=ATSScoreOutput)
async def score_ats_resume(request: ATSScoreRequest):
    """
    Evaluates raw resume text against 5 weighted ATS criteria (Formatting, Keywords, Sections, Action Verbs, Impact).
    Returns ATSScoreOutput validated schema.
    """
    try:
        # Call Member 3 async ATS scoring method
        result = await openai_service.async_analyze_ats(
            resume_text=request.resume_text, target_jd=request.target_jd or ""
        )
        return result
    except Exception as e:
        # Raise HTTP 500 error if evaluation fails uncaught
        raise HTTPException(status_code=500, detail=f"ATS scoring failed: {str(e)}")


@app.post("/api/ats/star-rewrite", response_model=STARRewriteBatchOutput)
async def rewrite_star_bullets(request: STARRewriteRequest):
    """
    Rewrites a list of candidate bullet points into STAR-formatted metric-driven statements.
    Returns STARRewriteBatchOutput validated schema.
    """
    try:
        # Call Member 3 async STAR bullet rewriting method
        result = await openai_service.async_rewrite_star_bullets(
            bullet_points=request.bullet_points, target_jd=request.target_jd or ""
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STAR bullet rewrite failed: {str(e)}")


@app.post("/api/pipeline/process")
async def process_full_pipeline(
    file: UploadFile = File(...), target_jd: Optional[str] = Form("")
):
    """
    Upload resume file (PDF/DOCX) and execute master async processing pipeline across all services.
    """
    try:
        # Read raw byte content from uploaded file stream
        file_bytes = await file.read()
        # Execute master pipeline in orchestrator
        pipeline_result = await orchestrator.process_resume_pipeline(
            file_bytes=file_bytes, file_name=file.filename or "resume.pdf", target_jd=target_jd or ""
        )
        return pipeline_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline processing failed: {str(e)}")


# =====================================================================
# Member 4 Gateway Endpoints (Master Project Plan Page 3 & 4)
# =====================================================================

# Import Member 4 schemas and matcher
from src.backend.models.schemas import (
    MasterAnalyzeResponse,
    JDMatchResult,
    DirectJDMatchRequest,
)
from src.backend.services.jd_matcher import match_jd_with_resume


@app.get("/", tags=["Root"])
def root_endpoint():
    """Service landing endpoint with system status."""
    return {
        "service": "Resume Doctor API Gateway",
        "version": "1.0.0",
        "status": "Operational",
        "docs_url": "/docs",
        "health_check": "/api/health"
    }


@app.get("/api/health", tags=["Monitoring"])
def api_health_check():
    """Detailed health check validating all 4 AI-103 and data modules."""
    return {
        "status": "Healthy",
        "modules": {
            "m1_doc_intel": "Active",
            "m2_ai_language": "Active",
            "m3_openai_ats": "Mock" if openai_service.is_mock_mode else "Live",
            "m4_jd_matcher": "Active (TF-IDF + Cosine Similarity)"
        }
    }


@app.post(
    "/api/analyze",
    response_model=MasterAnalyzeResponse,
    tags=["Core Pipeline"]
)
async def analyze_resume(
    resume_file: UploadFile = File(..., description="Resume PDF or DOCX file"),
    job_description: str = Form("", description="Target job description text"),
    target_role: Optional[str] = Form("", description="Optional target job title")
):
    """
    Master Ingestion Gateway Route (Member 4 Lead):
    Orchestrates all 4 modules:
    1. Member 1: Layout & table extraction (Doc Intelligence)
    2. Member 2: Sensitive entity redaction & NER (Azure AI Language)
    3. Concurrently via asyncio.gather():
       - Member 3: ATS Score & STAR bullet rewrite (Azure OpenAI)
       - Member 4: TF-IDF vectorization & Cosine Similarity match
    """
    filename = resume_file.filename or "resume.pdf"
    file_ext = filename.split(".")[-1].lower() if "." in filename else ""
    if file_ext not in ["pdf", "docx", "txt"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '.{file_ext}'. Please upload a PDF (.pdf) or DOCX (.docx) resume."
        )

    try:
        file_bytes = await resume_file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="The uploaded resume file is empty.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read resume file: {str(e)}")

    try:
        response = await orchestrator.analyze_to_model(
            file_bytes=file_bytes,
            filename=filename,
            job_description=job_description,
            target_role=target_role or ""
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline processing failed: {str(e)}")


@app.post(
    "/api/match-jd",
    response_model=JDMatchResult,
    tags=["Module 4 Direct"]
)
async def direct_match_jd(request: DirectJDMatchRequest):
    """
    Direct endpoint for testing TF-IDF Cosine Similarity and Skill Gap matching.
    """
    try:
        result = await match_jd_with_resume(
            clean_text=request.clean_text,
            jd_text=request.jd_text,
            resume_skills=request.resume_skills
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"JD match computation failed: {str(e)}")

