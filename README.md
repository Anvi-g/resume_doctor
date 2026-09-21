# Resume Doctor: Intelligent Resume Analyzer (Azure AI-103)

> **3-Day Ultra Sprint Master Project** | Target Completion: **September 18** | LMS Final Submission: **September 22**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19.0-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![Azure AI-103](https://img.shields.io/badge/Azure-AI--103_Services-0089D6?style=flat&logo=microsoftazure&logoColor=white)](https://azure.microsoft.com/)
[![pytest](https://img.shields.io/badge/tests-40%20passed-10B981?style=flat&logo=pytest&logoColor=white)](https://docs.pytest.org/)

---

## 📌 Executive Summary

**Resume Doctor** is an enterprise-grade, multi-service resume auditing and job matching platform powered by **Azure AI-103 services**. Designed for high accuracy and zero-friction parallel development, it extracts document structure, redacts sensitive PII, calculates semantic ATS fit against target job descriptions, and transforms weak resume bullet points into quantifiable **STAR-format** statements.

---

## 🏛️ System Architecture

```text
                               ┌─────────────────────────────────────────┐
                               │           React Web UI Dashboard        │
                               │        (Drag & Drop, Score Gauges)      │
                               └────────────────────┬────────────────────┘
                                                    │ POST /api/analyze
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │       FastAPI Gateway Orchestrator      │
                               │          (backend/app/main.py)          │
                               └────────────────────┬────────────────────┘
                                                    │
        ┌───────────────────────────┬───────────────┴───────────────┬───────────────────────────┐
        ▼                           ▼                               ▼                           ▼
┌──────────────────────┐  ┌───────────────────┐           ┌───────────────────┐       ┌───────────────────┐
│ Member 1: Doc Intel  │  │ Member 2: AI Lang │           │ Member 3: OpenAI  │       │ Member 4: JD      │
│  (Layout & Tables)   │  │  (PII Masking)    │           │ (ATS & STAR Gen)  │       │ (TF-IDF Matcher)  │
└──────────┬───────────┘  └─────────┬─────────┘           └─────────┬─────────┘       └─────────┬─────────┘
           │                        │                               │                           │
           └────────────────────────┴───────────────┬───────────────┴───────────────────────────┘
                                                    │ asyncio.gather()
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │          MasterAnalyzeResponse          │
                               │  (Doc, PII, ATS Score, STAR, JD Match)  │
                               └─────────────────────────────────────────┘
```

---

## 👥 Equal Team Work Division Matrix (20% Each)

| Member & Role | Technical Module Ownership | Key Responsibilities & Deliverables | 60s Video Segment |
| :--- | :--- | :--- | :--- |
| **Member 1** *(Team Lead)* | **Doc Intelligence & Orchestration** | • Azure Doc Intel layout & table parser<br/>• Local `pypdf` fallback parser<br/>• Master pipeline compilation & repo coordinator | **0:00 - 1:00**<br/>Intro, Project Overview, Problem Statement |
| **Member 2** *(NLP Lead)* | **Azure AI Language & PII Redaction** | • Reverse-offset PII masking (`[NAME]`, `[EMAIL]`, `[PHONE]`)<br/>• NER skill & certification extraction<br/>• `docs/responsible_ai.md` privacy standards | **1:00 - 2:00**<br/>Azure AI-103 Architecture & Privacy Flow |
| **Member 3** *(GenAI Lead)* | **Azure OpenAI ATS & STAR Rewriter** | • GPT-4o system prompt engineering<br/>• STAR format bullet rewrite engine (Situation, Task, Action, Result)<br/>• Validated Pydantic output schemas | **2:00 - 3:00**<br/>Live Demo Part 1 (Doc Upload, PII, ATS Score) |
| **Member 4** *(Data Lead)* | **JD Matcher & Backend Gateway** | • TF-IDF vectorization & Cosine Similarity match algorithm<br/>• Skill gap matrix (% match, matched vs missing skills)<br/>• FastAPI `/api/analyze` gateway route & `asyncio.gather()` | **3:00 - 4:00**<br/>Live Demo Part 2 (JD Matcher & STAR Rewrites) |
| **Member 5** *(Frontend Lead)* | **Interactive Web UI Dashboard** | • React/Vite dashboard UI<br/>• Animated score gauges & step progress indicators<br/>• Redacted PII toggle & copy-to-clipboard STAR cards | **4:00 - 5:00**<br/>Dashboard Demo, Responsible AI & Wrap-up |

---

## 🚀 Quickstart Guide

### Prerequisites
- **Python**: `3.10+`
- **Node.js**: `v18+` (npm `v9+`)

### 1. Backend Setup & Run
```bash
# Clone repository
git clone <repo-url>
cd azure_ai_103

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install backend dependencies
pip install -r requirements.txt

# Configure environment variables (optional for offline mock mode)
cp .env.example .env

# Run FastAPI Gateway server
uvicorn backend.app.main:app --reload --port 8000
```
*Backend API Docs will be available at:* `http://localhost:8000/docs`

### 2. Frontend Setup & Run
```bash
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Start Vite React dev server
npm run dev
```
*Frontend UI Dashboard will be available at:* `http://localhost:5173`

### 3. Running Unit Test Suite
```bash
./venv/bin/pytest
```

---

## 🔗 Shared API Endpoints & Pydantic Data Contracts

### 1. `POST /api/analyze` (Master Ingestion Route)
Accepts a multipart resume file (`PDF` or `DOCX`) and an optional `job_description` string. Executes all 4 AI modules and returns `MasterAnalyzeResponse`:

```json
{
  "doc_summary": {
    "raw_text": "John Doe...",
    "page_count": 1,
    "tables": [],
    "file_type": "pdf"
  },
  "pii_summary": {
    "clean_text": "[NAME]\nSoftware Engineer...",
    "detected_pii": [{"type": "Person", "text": "John Doe"}],
    "extracted_skills": ["Python", "FastAPI", "Azure"],
    "extracted_certifications": ["Azure AI-103"]
  },
  "ats_analysis": {
    "ats_score": 88,
    "strengths": ["Clear action verbs", "Relevant skill section"],
    "weaknesses": ["Unquantified metric bullet points"],
    "star_rewrites": [
      {
        "original": "Built REST APIs with Python",
        "improved_star": "Engineered 12+ RESTful microservices using Python and FastAPI, reducing response latency by 35%.",
        "impact_metric": "35% latency reduction"
      }
    ]
  },
  "jd_match": {
    "match_percentage": 85.0,
    "matched_skills": ["Python", "FastAPI", "Azure"],
    "missing_skills": ["Kubernetes"],
    "recommendations": ["Add evidence of experience with Kubernetes."]
  }
}
```

---

## 🛡️ Responsible AI & Privacy Guarantees

For detailed information regarding our data governance, PII masking algorithms, and ethical AI safeguards, see [`docs/responsible_ai.md`](docs/responsible_ai.md).

- **Data Privacy**: No raw user PII is sent to external GenAI endpoints; sensitive entities are masked locally beforehand.
- **Fairness & Bias**: ATS evaluation focuses exclusively on technical skill overlap, formatting structure, and metric quantification.
