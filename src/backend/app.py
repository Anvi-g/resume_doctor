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
