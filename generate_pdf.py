import sys
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header line & text on pages 2+
        if self._pageNumber > 1:
            self.drawString(28.8, 762, "RESUME DOCTOR: 3-DAY ULTRA SPRINT MASTER PROJECT PLAN")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(28.8, 755, 583.2, 755)

        # Footer
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(583.2, 20, page_str)
        self.drawString(28.8, 20, "CONFIDENTIAL & PROPRIETARY — AZURE AI-103 PROJECT TEAM")
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(28.8, 30, 583.2, 30)
        self.restoreState()

def create_pdf(filename="/home/anvi/Work/azure_ai_103/Resume_Doctor_Master_Project_Plan.pdf"):
    # Margins: 0.4 inches (28.8 pt)
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=28.8,
        rightMargin=28.8,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Colors
    PRIMARY = colors.HexColor("#0F2C59")        # Deep Navy
    SECONDARY = colors.HexColor("#1E40AF")      # Royal Blue
    ACCENT_BG = colors.HexColor("#FEF3C7")      # Amber Light
    ACCENT_BORDER = colors.HexColor("#D97706")  # Amber Border
    TABLE_HEADER_BG = colors.HexColor("#1E3A8A")
    ROW_BG_ALT = colors.HexColor("#F8FAFC")
    HIGHLIGHT_BG = colors.HexColor("#DCFCE7")    # Soft Green
    TEXT_DARK = colors.HexColor("#1E293B")
    CODE_BG = colors.HexColor("#F1F5F9")
    CODE_BORDER = colors.HexColor("#CBD5E1")

    # Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=PRIMARY,
        alignment=1,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=SECONDARY,
        alignment=1,
        spaceAfter=8
    )

    callout_style = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#92400E"),
        alignment=1
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=PRIMARY,
        spaceBefore=10,
        spaceAfter=4
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=SECONDARY,
        spaceBefore=6,
        spaceAfter=3
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=TEXT_DARK,
        spaceAfter=4
    )

    code_style = ParagraphStyle(
        'Code_Custom',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#0F172A")
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=0
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=TEXT_DARK
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=10,
        textColor=TEXT_DARK
    )

    story = []

    # =========================================================================
    # PAGE 1: EXECUTIVE SUMMARY & DAY-BY-DAY SCHEDULE
    # =========================================================================
    story.append(Paragraph("RESUME DOCTOR: 3-DAY ULTRA SPRINT PROJECT PLAN", title_style))
    story.append(Paragraph("Target Completion: September 18 | LMS Lock & Review Buffer: Sept 19 – 21 | Final LMS Submission: Sept 22", subtitle_style))

    # Guarantee Callout Banner
    callout_data = [[Paragraph("ULTRA SPRINT GUARANTEE: Full Code Freeze, 5-Min Video & Zero-Issue Lock Completed by September 18", callout_style)]]
    callout_table = Table(callout_data, colWidths=[554.4])
    callout_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), ACCENT_BG),
        ('BOX', (0,0), (-1,-1), 1.2, ACCENT_BORDER),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(callout_table)
    story.append(Spacer(1, 6))

    # Section 1: Executive Summary
    story.append(Paragraph("1. Executive Summary & Tech Stack", h1_style))
    exec_summary_text = (
        "<b>Resume Doctor</b> is an intelligent resume analyzer built with Azure AI-103 services. "
        "To meet urgent delivery deadlines, the project schedule is compressed into a hyper-accelerated <b>3-day ultra sprint (Sept 16 – Sept 18)</b> "
        "for a 5-member team. Member 1 acts as <b>Team Lead</b> managing orchestration, releases, and LMS submission. "
        "To ensure seamless parallel work on Day 1, this master document defines the exact shared directory architecture, Pydantic interface contracts, "
        "function signatures, and step-by-step member deliverables so each member works independently with zero integration friction."
    )
    story.append(Paragraph(exec_summary_text, body_style))
    story.append(Spacer(1, 4))

    # Section 2: Accelerated Schedule Table
    story.append(Paragraph("2. Accelerated Day-by-Day Schedule (Sept 16 – Sept 18)", h1_style))

    sched_headers = [
        Paragraph("Date & Day", table_header_style),
        Paragraph("Milestone & Objectives", table_header_style),
        Paragraph("Key Deliverables & Responsible Members", table_header_style)
    ]

    sched_data = [
        sched_headers,
        [
            Paragraph("<b>Sept 16</b><br/>(Day 1)", table_cell_bold),
            Paragraph("<b>Core Module Coding & Gateway Integration</b>", table_cell_style),
            Paragraph("Independent module builds: Doc Intel (M1), PII/NLP (M2), OpenAI Prompts (M3), JD Matcher (M4), UI Layout (M5). FastAPI <code>/api/analyze</code> gateway connected to all AI modules & Frontend UI. First end-to-end dry run. <i>All Members</i>", table_cell_style)
        ],
        [
            Paragraph("<b>Sept 17</b><br/>(Day 2)", table_cell_bold),
            Paragraph("<b>Testing, Optimization & Docs Audit</b>", table_cell_style),
            Paragraph("Test 15+ resume formats (PDF/DOCX, multi-column). Write unit test suite (<code>pytest</code>). Resolve latency issues. Zero-keys scan (no secrets in git). Complete <code>README.md</code> & <code>responsible_ai.md</code>. Verify PII masking. <i>All Members</i>", table_cell_style)
        ],
        [
            Paragraph("<b>Sept 18</b><br/>(Day 3)", table_cell_bold),
            Paragraph("<b>CODE FREEZE, VIDEO & ZERO-ISSUE LOCK</b>", table_cell_bold),
            Paragraph("<b>Hard Code Freeze at 12 PM.</b> Record 5-min video (60s each). Upload to YouTube (test link access). Final repository lock, link verification, zero-issues sign-off. Project 100% ready for LMS. <i>All Members (M1 Lead)</i>", table_cell_style)
        ],
        [
            Paragraph("<b>Sept 19–21</b><br/>(Buffer)", table_cell_bold),
            Paragraph("<b>LMS Buffer & Final Review</b>", table_cell_style),
            Paragraph("Zero active coding required. Reserved for final peer review, YouTube link access check, and early LMS submission prior to Sept 22 deadline. <i>M1 (Team Lead)</i>", table_cell_style)
        ]
    ]

    sched_table = Table(sched_data, colWidths=[65, 140, 349.4])
    sched_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), TABLE_HEADER_BG),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, ROW_BG_ALT]),
        ('BACKGROUND', (0,3), (-1,3), HIGHLIGHT_BG),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(sched_table)
    story.append(Spacer(1, 6))

    # Section 3: Work Division Matrix
    story.append(Paragraph("3. Equal Team Work Division Matrix (20% Each)", h1_style))

    matrix_headers = [
        Paragraph("Member & Role", table_header_style),
        Paragraph("Technical Module Ownership", table_header_style),
        Paragraph("Responsibilities", table_header_style),
        Paragraph("60s Video Segment", table_header_style)
    ]

    matrix_data = [
        matrix_headers,
        [
            Paragraph("<b>Member 1</b><br/>(Team Lead)", table_cell_bold),
            Paragraph("Doc Intelligence & Orchestration", table_cell_style),
            Paragraph("• Azure Doc Intel layout parser<br/>• Master pipeline compilation<br/>• GitHub releases & LMS coordinator", table_cell_style),
            Paragraph("<b>0:00 - 1:00</b><br/>Intro, Team Lead Overview, Problem Statement", table_cell_style)
        ],
        [
            Paragraph("<b>Member 2</b><br/>(NLP Lead)", table_cell_bold),
            Paragraph("Azure AI Language & PII Redaction", table_cell_style),
            Paragraph("• Azure PII detection & masking<br/>• NER skill & cert extraction<br/>• Responsible AI privacy docs", table_cell_style),
            Paragraph("<b>1:00 - 2:00</b><br/>Azure AI-103 Architecture & Data Flow", table_cell_style)
        ],
        [
            Paragraph("<b>Member 3</b><br/>(GenAI Lead)", table_cell_bold),
            Paragraph("Azure OpenAI ATS & STAR Rewriter", table_cell_style),
            Paragraph("• GPT-4o ATS score prompts<br/>• STAR bullet rewrite engine<br/>• JSON response validator", table_cell_style),
            Paragraph("<b>2:00 - 3:00</b><br/>Live Demo Part 1 (Doc Upload, PII, Score)", table_cell_style)
        ],
        [
            Paragraph("<b>Member 4</b><br/>(Data Lead)", table_cell_bold),
            Paragraph("JD Matcher & Backend Gateway", table_cell_style),
            Paragraph("• Job Description parser<br/>• Skill Gap % match algorithm<br/>• FastAPI endpoint routing", table_cell_style),
            Paragraph("<b>3:00 - 4:00</b><br/>Live Demo Part 2 (JD Matcher & Rewrites)", table_cell_style)
        ],
        [
            Paragraph("<b>Member 5</b><br/>(Frontend Lead)", table_cell_bold),
            Paragraph("Interactive Web UI Dashboard", table_cell_style),
            Paragraph("• React/Streamlit dashboard<br/>• Drag & drop uploader + spinner<br/>• Score gauges & Before/After cards", table_cell_style),
            Paragraph("<b>4:00 - 5:00</b><br/>Impact, Responsible AI, Wrap-up", table_cell_style)
        ]
    ]

    matrix_table = Table(matrix_data, colWidths=[75, 115, 234.4, 130])
    matrix_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), TABLE_HEADER_BG),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, ROW_BG_ALT]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(matrix_table)

    # Page Break -> Page 2
    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: SHARED TECHNICAL ARCHITECTURE & PYDANTIC CONTRACTS
    # =========================================================================
    story.append(Paragraph("4. Shared Technical Architecture & Data Contracts", h1_style))
    story.append(Paragraph(
        "To allow all 5 members to write code simultaneously without breaking integration, all services strictly implement the directory layout "
        "and Pydantic schemas specified below.", body_style
    ))
    story.append(Spacer(1, 4))

    story.append(Paragraph("Project Directory Structure", h2_style))
    dir_tree_code = (
        "resume_doctor/\n"
        "├── backend/\n"
        "│   ├── app/\n"
        "│   │   ├── main.py                    # FastAPI Gateway (Member 4 Lead)\n"
        "│   │   ├── config.py                  # Pydantic Settings & Azure Envs (Member 1 Lead)\n"
        "│   │   ├── models/\n"
        "│   │   │   └── schemas.py             # Shared Interface Contracts (Member 1 Lead)\n"
        "│   │   └── services/\n"
        "│   │       ├── doc_intel.py           # Module 1: Document Layout Parser (Member 1)\n"
        "│   │       ├── pii_redactor.py        # Module 2: PII Detection & NER (Member 2)\n"
        "│   │       ├── openai_ats.py          # Module 3: GPT-4o ATS & STAR Engine (Member 3)\n"
        "│   │       └── jd_matcher.py          # Module 4: JD Skill Gap Analyzer (Member 4)\n"
        "│   └── tests/                         # Pytest Integration Suite\n"
        "├── frontend/                          # Module 5: Web UI Dashboard (Member 5)\n"
        "├── docs/                              # README.md & responsible_ai.md\n"
        "└── .env.example"
    )
    dir_table = Table([[Paragraph(dir_tree_code.replace('\n', '<br/>').replace(' ', '&nbsp;'), code_style)]], colWidths=[554.4])
    dir_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), CODE_BG),
        ('BOX', (0,0), (-1,-1), 0.5, CODE_BORDER),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(dir_table)
    story.append(Spacer(1, 6))

    story.append(Paragraph("Shared Pydantic Interface Contracts (backend/app/models/schemas.py)", h2_style))
    
    pydantic_code_text = (
        "from pydantic import BaseModel, Field<br/><br/>"
        "<b># --- Module 1 Output Schema ---</b><br/>"
        "class ParseResumeResponse(BaseModel):<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;raw_text: str<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;page_count: int<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;tables: list[dict] = []<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;file_type: str  # 'pdf' | 'docx'<br/><br/>"
        "<b># --- Module 2 Output Schema ---</b><br/>"
        "class RedactPIIResponse(BaseModel):<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;clean_text: str  # Masked with [NAME], [EMAIL], [PHONE], etc.<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;detected_pii: list[dict]  # [{'type': 'Person', 'text': 'John', 'confidence': 0.98}]<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;extracted_skills: list[str]<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;extracted_certifications: list[str]<br/><br/>"
        "<b># --- Module 3 Output Schema ---</b><br/>"
        "class StarRewrite(BaseModel):<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;original: str<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;improved_star: str<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;impact_metric: str<br/><br/>"
        "class ATSAnalysisResult(BaseModel):<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;ats_score: int = Field(..., ge=0, le=100)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;strengths: list[str]<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;weaknesses: list[str]<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;star_rewrites: list[StarRewrite]<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;format_issues: list[str]<br/><br/>"
        "<b># --- Module 4 Output Schema ---</b><br/>"
        "class JDMatchResult(BaseModel):<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;match_percentage: float = Field(..., ge=0.0, le=100.0)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;matched_skills: list[str]<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;missing_skills: list[str]<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;recommendations: list[str]<br/><br/>"
        "<b># --- Master Gateway Response (POST /api/analyze) ---</b><br/>"
        "class MasterAnalyzeResponse(BaseModel):<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;doc_summary: ParseResumeResponse<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;pii_summary: RedactPIIResponse<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;ats_analysis: ATSAnalysisResult<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;jd_match: JDMatchResult"
    )

    schema_table = Table([[Paragraph(pydantic_code_text, code_style)]], colWidths=[554.4])
    schema_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), CODE_BG),
        ('BOX', (0,0), (-1,-1), 0.5, CODE_BORDER),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(schema_table)

    # Page Break -> Page 3
    story.append(PageBreak())

    # =========================================================================
    # PAGE 3 & 4: DETAILED MEMBER-BY-MEMBER TASK SPECIFICATIONS
    # =========================================================================
    story.append(Paragraph("5. Member-by-Member Detailed Technical Task Specifications", h1_style))
    story.append(Paragraph(
        "Each team member must strictly follow their assigned input/output function signatures, target files, and step-by-step task checklist.", body_style
    ))
    story.append(Spacer(1, 4))

    # Member 1 Box
    m1_content = (
        "<b>MEMBER 1: TEAM LEAD (Doc Intelligence & Orchestration Setup)</b><br/>"
        "• <b>Primary File:</b> <code>backend/app/services/doc_intel.py</code> | <b>Helpers:</b> <code>config.py</code>, <code>models/schemas.py</code>, <code>.env.example</code><br/>"
        "• <b>Azure Service:</b> Azure AI Document Intelligence (Model: <code>prebuilt-layout</code>)<br/>"
        "• <b>Exact Function Signature:</b> <code>async def parse_resume_layout(file_bytes: bytes, filename: str) -&gt; ParseResumeResponse</code><br/>"
        "• <b>Step-by-Step Task Checklist:</b><br/>"
        "&nbsp;&nbsp;1. Initialize Azure <code>DocumentAnalysisClient</code> using <code>AZURE_DOC_INTEL_ENDPOINT</code> and <code>AZURE_DOC_INTEL_KEY</code>.<br/>"
        "&nbsp;&nbsp;2. Process PDF and DOCX bytes to extract clean structured text line-by-line while preserving page boundaries.<br/>"
        "&nbsp;&nbsp;3. Extract embedded tables (e.g. Work History & Education grids) into structured dictionary objects.<br/>"
        "&nbsp;&nbsp;4. Build an offline fallback parser using <code>pypdf</code> for unit testing without Azure cloud access.<br/>"
        "&nbsp;&nbsp;5. Create <code>.env.example</code> containing environment variable keys for all 5 team members."
    )
    m1_table = Table([[Paragraph(m1_content, body_style)]], colWidths=[554.4])
    m1_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F1F5F9")),
        ('BOX', (0,0), (-1,-1), 0.8, SECONDARY),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(m1_table)
    story.append(Spacer(1, 6))

    # Member 2 Box
    m2_content = (
        "<b>MEMBER 2: NLP LEAD (Azure AI Language & PII Redaction Engine)</b><br/>"
        "• <b>Primary File:</b> <code>backend/app/services/pii_redactor.py</code> | <b>Docs File:</b> <code>docs/responsible_ai.md</code><br/>"
        "• <b>Azure Service:</b> Azure AI Language (PII Detection & Named Entity Recognition - NER)<br/>"
        "• <b>Exact Function Signature:</b> <code>async def redact_pii_and_extract_entities(raw_text: str) -&gt; RedactPIIResponse</code><br/>"
        "• <b>Step-by-Step Task Checklist:</b><br/>"
        "&nbsp;&nbsp;1. Initialize <code>TextAnalyticsClient</code> using <code>AZURE_LANGUAGE_ENDPOINT</code> and <code>AZURE_LANGUAGE_KEY</code>.<br/>"
        "&nbsp;&nbsp;2. Call Azure PII Recognition API to detect <code>Person</code>, <code>Email</code>, <code>Phone</code>, <code>Address</code>, <code>SSN</code>.<br/>"
        "&nbsp;&nbsp;3. Replace detected PII characters with masked entity tags (e.g. <code>[NAME]</code>, <code>[EMAIL]</code>, <code>[PHONE]</code>).<br/>"
        "&nbsp;&nbsp;4. Call NER API to extract <code>Skill</code>, <code>Certification</code>, and <code>Organization</code> entity lists.<br/>"
        "&nbsp;&nbsp;5. Draft <code>docs/responsible_ai.md</code> detailing PII masking, data privacy protection, and ethical AI standards."
    )
    m2_table = Table([[Paragraph(m2_content, body_style)]], colWidths=[554.4])
    m2_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F1F5F9")),
        ('BOX', (0,0), (-1,-1), 0.8, SECONDARY),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(m2_table)
    story.append(Spacer(1, 6))

    # Member 3 Box
    m3_content = (
        "<b>MEMBER 3: GENAI LEAD (Azure OpenAI ATS Scoring & STAR Bullet Rewriter)</b><br/>"
        "• <b>Primary File:</b> <code>backend/app/services/openai_ats.py</code><br/>"
        "• <b>Azure Service:</b> Azure OpenAI (Deployment: <code>gpt-4o</code>)<br/>"
        "• <b>Exact Function Signature:</b> <code>async def evaluate_ats_and_rewrite_star(clean_text: str, target_role: str = \"\") -&gt; ATSAnalysisResult</code><br/>"
        "• <b>Step-by-Step Task Checklist:</b><br/>"
        "&nbsp;&nbsp;1. Initialize <code>AsyncAzureOpenAI</code> client using <code>AZURE_OPENAI_ENDPOINT</code> and <code>AZURE_OPENAI_KEY</code>.<br/>"
        "&nbsp;&nbsp;2. Engineer system prompt instructing GPT-4o to act as a Recruiter and output strictly valid JSON.<br/>"
        "&nbsp;&nbsp;3. Calculate ATS Score (0-100) evaluating formatting, keyword density, section headers, and action verbs.<br/>"
        "&nbsp;&nbsp;4. Identify weak bullet points and rewrite them into STAR format (Situation, Task, Action, Result) with impact metrics.<br/>"
        "&nbsp;&nbsp;5. Validate returned JSON using Pydantic <code>ATSAnalysisResult</code> schema to guarantee zero runtime crashes."
    )
    m3_table = Table([[Paragraph(m3_content, body_style)]], colWidths=[554.4])
    m3_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F1F5F9")),
        ('BOX', (0,0), (-1,-1), 0.8, SECONDARY),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(m3_table)
    story.append(Spacer(1, 6))

    # Member 4 Box
    m4_content = (
        "<b>MEMBER 4: DATA LEAD (JD Matcher & FastAPI Gateway Orchestrator)</b><br/>"
        "• <b>Primary Files:</b> <code>backend/app/services/jd_matcher.py</code>, <code>backend/app/main.py</code> | <b>Test:</b> <code>backend/tests/test_gateway.py</code><br/>"
        "• <b>Exact Function Signatures:</b><br/>"
        "&nbsp;&nbsp;• <code>async def match_jd_with_resume(clean_text: str, jd_text: str, resume_skills: list[str]) -&gt; JDMatchResult</code><br/>"
        "&nbsp;&nbsp;• <code>@app.post(\"/api/analyze\", response_model=MasterAnalyzeResponse)</code><br/>"
        "• <b>Step-by-Step Task Checklist:</b><br/>"
        "&nbsp;&nbsp;1. Implement TF-IDF vectorization + Cosine Similarity matching algorithm between resume text and JD text.<br/>"
        "&nbsp;&nbsp;2. Calculate `match_percentage` (0-100%) and output `matched_skills` vs `missing_skills`.<br/>"
        "&nbsp;&nbsp;3. Build FastAPI `main.py` gateway route `POST /api/analyze` accepting `resume_file` and `job_description`.<br/>"
        "&nbsp;&nbsp;4. Orchestrate pipeline: Call M1 `parse_resume_layout` -&gt; M2 `redact_pii_and_extract_entities` -&gt; run M3 & M4 concurrently via `asyncio.gather()`.<br/>"
        "&nbsp;&nbsp;5. Write unit test suite (`pytest`) verifying end-to-end API response schemas."
    )
    m4_table = Table([[Paragraph(m4_content, body_style)]], colWidths=[554.4])
    m4_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F1F5F9")),
        ('BOX', (0,0), (-1,-1), 0.8, SECONDARY),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(m4_table)
    story.append(Spacer(1, 6))

    # Member 5 Box
    m5_content = (
        "<b>MEMBER 5: FRONTEND LEAD (Interactive Web UI Dashboard)</b><br/>"
        "• <b>Primary Directory:</b> <code>frontend/</code> (React or Streamlit Dashboard)<br/>"
        "• <b>Target API Endpoint:</b> <code>POST http://localhost:8000/api/analyze</code><br/>"
        "• <b>Step-by-Step Task Checklist:</b><br/>"
        "&nbsp;&nbsp;1. Build drag-and-drop resume upload zone (PDF/DOCX) + Job Description text area.<br/>"
        "&nbsp;&nbsp;2. Add interactive loading state with step indicators ('Parsing Layout...', 'Redacting PII...', 'Scoring ATS...').<br/>"
        "&nbsp;&nbsp;3. Render Animated Score Gauge (0-100%) for ATS score & JD match percentage.<br/>"
        "&nbsp;&nbsp;4. Build Redacted PII Toggle Card: View raw resume vs redacted resume with masked entity badges.<br/>"
        "&nbsp;&nbsp;5. Render Skill Gap Badges (Green for matched skills, Red for missing required skills).<br/>"
        "&nbsp;&nbsp;6. Create STAR Rewrite Cards comparing original bullets vs improved STAR bullets with a 'Copy to Clipboard' button."
    )
    m5_table = Table([[Paragraph(m5_content, body_style)]], colWidths=[554.4])
    m5_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F1F5F9")),
        ('BOX', (0,0), (-1,-1), 0.8, SECONDARY),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(m5_table)
    story.append(Spacer(1, 8))

    # Section 6: Video Script & Final Checklist
    story.append(Paragraph("6. 5-Minute YouTube Video Script & Final Checklist", h1_style))

    checklist_items = [
        "<b>Video Script (60s each):</b> 0:00-1:00 Member 1 Intro & Overview | 1:00-2:00 Member 2 Architecture & PII | 2:00-3:00 Member 3 Demo P1 (ATS & STAR) | 3:00-4:00 Member 4 Demo P2 (JD Matcher & Gateway) | 4:00-5:00 Member 5 Dashboard & LMS Wrap-up.",
        "<b>September 18 (12:00 PM Code Freeze):</b> All feature branches merged to master. Video recorded, edited, and uploaded to YouTube with Unlisted/Public test access.",
        "<b>September 18 (5:00 PM Zero-Issue Lock):</b> Repo tested end-to-end, YouTube link verified, <code>README.md</code> checked, repository locked. Project 100% complete.",
        "<b>September 19 – 21 (Review Buffer):</b> Secondary verification window and early LMS link submission.",
        "<b>September 22 (Hard Deadline):</b> Final LMS submission complete."
    ]

    for item in checklist_items:
        story.append(Paragraph(f"• {item}", body_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print("Successfully generated fully detailed multi-page PDF!")

if __name__ == '__main__':
    create_pdf()
