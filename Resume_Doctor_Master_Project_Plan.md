    # RESUME DOCTOR: 3-DAY ULTRA SPRINT PROJECT PLAN
**Target Completion: September 18** | **LMS Lock & Review Buffer: September 19 – 21** | **Final LMS Submission: September 22**

> [!IMPORTANT]
> **ULTRA SPRINT GUARANTEE:** Full Code Freeze, 5-Minute YouTube Video Recording, and Zero-Issue Lock will be completed by **September 18, 2026**.

---

## 1. Executive Summary & Tech Stack

**Resume Doctor** is an intelligent resume analyzer built with Azure AI-103 services. To meet urgent delivery deadlines, the project schedule has been compressed into a hyper-accelerated **3-day ultra sprint (September 16 – September 18)** for a 5-member team. 

Member 1 acts as **Team Lead** managing orchestration, releases, and LMS submission. All core module development, FastAPI integration, automated testing, security audit, video demo recording, and repository lock are fully finalized by **September 18**, leaving September 19–21 as a risk-free buffer before the final LMS deadline on September 22.

---

## 2. Accelerated Day-by-Day Schedule (Sept 16 – Sept 18)

| Date & Day | Milestone & Objectives | Key Deliverables & Responsible Members |
| :--- | :--- | :--- |
| **Sept 16** *(Day 1)* | **Core Module Coding & Gateway Integration** | Independent module builds: Doc Intel (M1), PII/NLP (M2), OpenAI Prompts (M3), JD Matcher (M4), UI Layout (M5). FastAPI `/api/analyze` gateway connected to all AI modules & Frontend UI. First end-to-end dry run. <br/>*Responsible: All Members* |
| **Sept 17** *(Day 2)* | **Testing, Optimization & Docs Audit** | Test 15+ resume formats (PDF/DOCX, multi-column). Write unit test suite (`pytest`). Resolve latency issues. Zero-keys scan (no secrets in git). Complete `README.md` & `responsible_ai.md`. Verify PII masking. <br/>*Responsible: All Members* |
| **Sept 18** *(Day 3)* | **CODE FREEZE, VIDEO & ZERO-ISSUE LOCK** | **Hard Code Freeze at 12:00 PM.** Record 5-min video (60s each). Upload to YouTube (test link access). Final repository lock, link verification, zero-issues sign-off. Project 100% ready for LMS. <br/>*Responsible: All Members (M1 Lead)* |
| **Sept 19 – 21** *(Buffer)* | **LMS Buffer & Final Review** | Zero active coding required. Reserved for final peer review, YouTube link access check, and early LMS submission prior to Sept 22 deadline. <br/>*Responsible: M1 (Team Lead)* |

---

## 3. Equal Team Work Division Matrix (20% Each)

| Member & Role | Technical Module Ownership | Responsibilities | 60s Video Segment |
| :--- | :--- | :--- | :--- |
| **Member 1** *(Team Lead)* | Doc Intelligence & Orchestration | • Azure Doc Intel layout parser<br/>• Master pipeline compilation<br/>• GitHub releases & LMS coordinator | **0:00 - 1:00**<br/>Intro, Team Lead Overview, Problem Statement |
| **Member 2** *(NLP Lead)* | Azure AI Language & PII Redaction | • Azure PII detection & masking<br/>• NER skill & cert extraction<br/>• Responsible AI privacy docs | **1:00 - 2:00**<br/>Azure AI-103 Architecture & Data Flow |
| **Member 3** *(GenAI Lead)* | Azure OpenAI ATS & STAR Rewriter | • GPT-4o ATS score prompts<br/>• STAR bullet rewrite engine<br/>• JSON response validator | **2:00 - 3:00**<br/>Live Demo Part 1 (Doc Upload, PII, Score) |
| **Member 4** *(Data Lead)* | JD Matcher & Backend Gateway | • Job Description parser<br/>• Skill Gap % match algorithm<br/>• FastAPI endpoint routing | **3:00 - 4:00**<br/>Live Demo Part 2 (JD Matcher & Rewrites) |
| **Member 5** *(Frontend Lead)* | Interactive Web UI Dashboard | • React/Streamlit dashboard<br/>• Drag & drop uploader + spinner<br/>• Score gauges & Before/After cards | **4:00 - 5:00**<br/>Impact, Responsible AI, Wrap-up |

---

## 4. Shared Technical Architecture & Data Contracts (Zero-Friction Integration)

To allow all 5 members to work completely independently on Day 1 without integration conflicts, all modules adhere to strict directory layouts and Pydantic data models.

### Directory Layout
```text
resume_doctor/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI Gateway (Member 4)
│   │   ├── config.py                  # Pydantic Settings & Env Setup (Member 1)
│   │   ├── models/
│   │   │   └── schemas.py             # Shared Pydantic Contracts (Member 1)
│   │   └── services/
│   │       ├── doc_intel.py           # Module 1: Document Layout Parser (Member 1)
│   │       ├── pii_redactor.py        # Module 2: PII Detection & NER (Member 2)
│   │       ├── openai_ats.py          # Module 3: GPT-4o ATS & STAR Engine (Member 3)
│   │       └── jd_matcher.py          # Module 4: JD Skill Gap Analyzer (Member 4)
│   └── tests/                         # Pytest Integration Suite
├── frontend/                          # Module 5: Web UI Dashboard (Member 5)
├── docs/                              # README.md & responsible_ai.md
└── .env.example
```

### Shared Pydantic Data Contracts (`backend/app/models/schemas.py`)

```python
from pydantic import BaseModel, Field

# --- Module 1 Output Schema ---
class ParseResumeResponse(BaseModel):
    raw_text: str
    page_count: int
    tables: list[dict] = []
    file_type: str  # "pdf" | "docx"

# --- Module 2 Output Schema ---
class RedactPIIResponse(BaseModel):
    clean_text: str  # PII masked with [NAME], [EMAIL], [PHONE], etc.
    detected_pii: list[dict]  # [{"type": "Person", "text": "John Doe", "confidence": 0.98}]
    extracted_skills: list[str]
    extracted_certifications: list[str]

# --- Module 3 Output Schema ---
class StarRewrite(BaseModel):
    original: str
    improved_star: str
    impact_metric: str

class ATSAnalysisResult(BaseModel):
    ats_score: int = Field(..., ge=0, le=100)
    strengths: list[str]
    weaknesses: list[str]
    star_rewrites: list[StarRewrite]
    format_issues: list[str]

# --- Module 4 Output Schema ---
class JDMatchResult(BaseModel):
    match_percentage: float = Field(..., ge=0.0, le=100.0)
    matched_skills: list[str]
    missing_skills: list[str]
    recommendations: list[str]

# --- Master Gateway Response (POST /api/analyze) ---
class MasterAnalyzeResponse(BaseModel):
    doc_summary: ParseResumeResponse
    pii_summary: RedactPIIResponse
    ats_analysis: ATSAnalysisResult
    jd_match: JDMatchResult
```

---

## 5. Member-by-Member Exact Task & Module Specifications

### 👤 Member 1: Team Lead (Doc Intelligence & Base Setup)
- **Primary File**: `backend/app/services/doc_intel.py`
- **Helper Files**: `backend/app/config.py`, `backend/app/models/schemas.py`, `.env.example`
- **Azure Service**: Azure AI Document Intelligence (`prebuilt-layout` model)
- **Exact Function Signature**:
  ```python
  async def parse_resume_layout(file_bytes: bytes, filename: str) -> ParseResumeResponse
  ```
- **Step-by-Step Deliverables**:
  1. Initialize Azure `DocumentAnalysisClient` using `AZURE_DOC_INTEL_ENDPOINT` and `AZURE_DOC_INTEL_KEY`.
  2. Implement `parse_resume_layout` to process PDF/DOCX bytes and extract structured text line-by-line while preserving page numbers.
  3. Extract embedded tables (e.g., Work History/Education grids) into structured dictionary objects.
  4. Implement a lightweight local fallback parser using `pypdf` for offline testing.
  5. Provide `.env.example` containing configuration variables for all 5 members.

---

### 👤 Member 2: NLP Lead (Azure AI Language & PII Redaction)
- **Primary File**: `backend/app/services/pii_redactor.py`
- **Docs File**: `docs/responsible_ai.md`
- **Azure Service**: Azure AI Language (PII Detection & Named Entity Recognition)
- **Exact Function Signature**:
  ```python
  async def redact_pii_and_extract_entities(raw_text: str) -> RedactPIIResponse
  ```
- **Step-by-Step Deliverables**:
  1. Initialize `TextAnalyticsClient` using `AZURE_LANGUAGE_ENDPOINT` and `AZURE_LANGUAGE_KEY`.
  2. Call Azure PII recognition API to detect `Person`, `Email`, `Phone`, `Address`, `SSN`.
  3. Replace detected PII characters with masked placeholders (`[NAME]`, `[EMAIL]`, `[PHONE]`, `[ADDRESS]`).
  4. Call NER (Named Entity Recognition) to extract `Skill`, `Certification`, and `Organization` entities.
  5. Draft `docs/responsible_ai.md` explaining PII masking, data privacy guarantees, and ethical AI standards.

---

### 👤 Member 3: GenAI Lead (Azure OpenAI ATS & STAR Rewriter)
- **Primary File**: `backend/app/services/openai_ats.py`
- **Azure Service**: Azure OpenAI (GPT-4o deployment)
- **Exact Function Signature**:
  ```python
  async def evaluate_ats_and_rewrite_star(clean_text: str, target_role: str = "") -> ATSAnalysisResult
  ```
- **Step-by-Step Deliverables**:
  1. Initialize `AsyncAzureOpenAI` client using `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY`, and `AZURE_OPENAI_DEPLOYMENT`.
  2. Write system prompt instructing GPT-4o to act as a Senior Technical Recruiter and output strictly valid JSON matching `ATSAnalysisResult`.
  3. Compute an ATS score (0-100) evaluating formatting, keyword density, section headers, and action verbs.
  4. Identify weak bullet points (lacking quantification or structure) and convert them to high-impact STAR format (Situation, Task, Action, Result).
  5. Validate returned JSON using Pydantic `ATSAnalysisResult` schema to ensure zero runtime crashes.

---

### 👤 Member 4: Data Lead (JD Matcher & FastAPI Gateway Orchestrator)
- **Primary Files**: `backend/app/services/jd_matcher.py`, `backend/app/main.py`
- **Test File**: `backend/tests/test_gateway.py`
- **Exact Function Signatures**:
  ```python
  # Module 4 Core
  async def match_jd_with_resume(clean_text: str, jd_text: str, resume_skills: list[str]) -> JDMatchResult

  # FastAPI Endpoint in main.py
  @app.post("/api/analyze", response_model=MasterAnalyzeResponse)
  async def analyze_resume(resume_file: UploadFile = File(...), job_description: str = Form(""))
  ```
- **Step-by-Step Deliverables**:
  1. Implement `match_jd_with_resume` using TF-IDF vectorization + Cosine Similarity and skill set intersection.
  2. Calculate `match_percentage` (0.0 to 100.0%) and categorize skills into `matched_skills` vs `missing_skills`.
  3. Build FastAPI `main.py` backend gateway route `POST /api/analyze`.
  4. Orchestrate module execution pipeline: Call `parse_resume_layout` (M1) -> `redact_pii_and_extract_entities` (M2) -> run `evaluate_ats_and_rewrite_star` (M3) and `match_jd_with_resume` (M4) concurrently with `asyncio.gather()`.
  5. Write `pytest` suite testing all endpoints with sample resume inputs.

---

### 👤 Member 5: Frontend Lead (Interactive Web UI Dashboard)
- **Primary Directory**: `frontend/` (React or Streamlit)
- **API Target**: `POST http://localhost:8000/api/analyze`
- **Step-by-Step Deliverables**:
  1. Build clean, modern UI layout featuring drag-and-drop file upload for PDF/DOCX and a text area for Job Description input.
  2. Add interactive loading state with step progress indicators (e.g., "Extracting Layout...", "Redacting PII...", "Evaluating ATS...").
  3. Render **Animated Score Gauge** (0–100%) displaying ATS score and JD Match %.
  4. Build **PII Privacy Toggle Card**: View raw resume vs redacted resume with masked badges (`[NAME]`, `[EMAIL]`).
  5. Display **Skill Gap Badges**: Green pill tags for matched skills and Red pill tags for missing required skills.
  6. Create **STAR Rewrite Cards**: Side-by-side comparison of original bullet points vs improved STAR bullets with a "Copy to Clipboard" button.

---

## 6. 5-Minute YouTube Video Script & Final Checklist

- **Video Script (60s per member):**
  - `0:00 - 1:00`: Member 1 — Introduction, Project Scope & Doc Intel Parsing
  - `1:00 - 2:00`: Member 2 — Azure AI-103 Architecture, PII Masking & Privacy Docs
  - `2:00 - 3:00`: Member 3 — Live Demo Part 1 (ATS Score & STAR Bullet Rewriter)
  - `3:00 - 4:00`: Member 4 — Live Demo Part 2 (JD Skill Gap Matcher & FastAPI Gateway)
  - `4:00 - 5:00`: Member 5 — Interactive UI Dashboard, Impact & LMS Wrap-up
- **September 18 (12:00 PM Code Freeze):** All feature branches merged to master. Video recorded, edited, and uploaded to YouTube with Unlisted/Public test access.
- **September 18 (5:00 PM Zero-Issue Lock):** Repo tested end-to-end, YouTube video link verified, `README.md` checked, repository locked. Project 100% complete.
- **September 19 – 21 (Review Buffer):** Secondary verification window and early LMS link submission.
- **September 22 (Hard Deadline):** Final LMS submission complete.
