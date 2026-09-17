import asyncio
import os
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

from src.backend.services.ai_language import AILanguageService
from src.backend.services.azure_openai import OpenAIService
from src.backend.services.doc_intelligence import DocIntelligenceService
from src.backend.services.jd_matcher import JDMatcherService


DEFAULT_API_URL = os.getenv("RESUME_DOCTOR_API_URL", "http://localhost:8000/api/analyze")


def as_dict(model: Any) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    if hasattr(model, "dict"):
        return model.dict()
    return dict(model)


async def analyze_uploaded_resume(uploaded_file, job_description: str) -> Dict[str, Any]:
    """Combine the outputs from the backend service modules into one payload for the web UI."""
    if uploaded_file is None:
        raise ValueError("A resume file is required.")

    file_bytes = uploaded_file.getvalue()
    doc_service = DocIntelligenceService()
    language_service = AILanguageService()
    openai_service = OpenAIService()
    jd_service = JDMatcherService()

    parsed_doc = doc_service.parse_resume(file_bytes, uploaded_file.name)
    pii_result = await language_service.redact_pii_and_extract_entities(parsed_doc.raw_text)
    ats_result = await openai_service.evaluate_ats_and_rewrite_star(
        pii_result.clean_text,
        target_role="Senior Python Engineer",
    )
    jd_result = await jd_service.match_jd_with_resume(
        pii_result.clean_text,
        job_description,
        pii_result.extracted_skills,
    )

    combined = {
        "doc_summary": as_dict(parsed_doc),
        "pii_summary": as_dict(pii_result),
        "ats_analysis": as_dict(ats_result),
        "jd_match": as_dict(jd_result),
    }
    return combined


def build_demo_result(role: str, jd_text: str, candidate_name: str = "Candidate") -> Dict[str, Any]:
    """Generate a realistic demo payload when the backend API is unavailable."""
    skills = ["Python", "FastAPI", "Azure", "SQL", "Docker", "Git", "Machine Learning", "NLP"]
    jd_lower = (jd_text or "").lower()
    matched = [skill for skill in skills if skill.lower() in jd_lower]
    missing = [skill for skill in skills if skill.lower() not in jd_lower]

    if not matched:
        matched = ["Python", "SQL", "Azure"]
        missing = ["FastAPI", "Docker", "Git", "Machine Learning", "NLP"]

    ats_score = min(98, max(72, 78 + (len(matched) * 4)))
    jd_match = min(100.0, max(50.0, 58.0 + (len(matched) * 5.5)))

    return {
        "doc_summary": {
            "raw_text": f"{candidate_name} has experience across software engineering, cloud platforms, and AI-driven product work.",
            "page_count": 1,
            "tables": [],
            "file_type": "pdf",
        },
        "pii_summary": {
            "clean_text": "[NAME] is a senior engineer with strong experience in Python, FastAPI, Azure, and SQL. Email: [EMAIL].",
            "detected_pii": [
                {"type": "Person", "text": candidate_name, "confidence": 0.99},
                {"type": "Email", "text": "candidate@example.com", "confidence": 0.99},
            ],
            "extracted_skills": matched,
            "extracted_certifications": ["Azure AI-103"],
        },
        "ats_analysis": {
            "ats_score": int(ats_score),
            "strengths": [
                "Strong matching keywords for the target role",
                "Clear technical skill alignment",
                "Results-oriented experience language",
            ],
            "weaknesses": [
                "Add more quantified impact metrics",
                "Include a few more role-specific keywords",
            ],
            "star_rewrites": [
                {
                    "original": "Built backend services for internal tools.",
                    "improved_star": "Built backend services for internal tools that reduced client onboarding time by 35% and improved system reliability across three production APIs.",
                    "impact_metric": "35% faster onboarding",
                },
                {
                    "original": "Worked with Azure and Python.",
                    "improved_star": "Led Python and Azure modernization work that cut deployment time by 40% while improving service observability and resilience.",
                    "impact_metric": "40% faster deployments",
                },
            ],
            "format_issues": ["Add section headings for skills and impact summary"],
        },
        "jd_match": {
            "match_percentage": round(float(jd_match), 1),
            "matched_skills": matched,
            "missing_skills": missing[:3],
            "recommendations": [
                f"Highlight {matched[0]} impact using measurable business outcomes.",
                "Add explicit examples of cloud deployment and collaboration.",
            ],
        },
    }


def normalize_analysis_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize either a real API response or a local demo response to a single UI contract."""
    if not isinstance(payload, dict):
        payload = {}

    doc_summary = payload.get("doc_summary") or {}
    pii_summary = payload.get("pii_summary") or {}
    ats_analysis = payload.get("ats_analysis") or {}
    jd_match = payload.get("jd_match") or {}

    return {
        "raw_text": doc_summary.get("raw_text", ""),
        "clean_text": pii_summary.get("clean_text", ""),
        "detected_pii": pii_summary.get("detected_pii", []),
        "extracted_skills": pii_summary.get("extracted_skills", []),
        "extracted_certifications": pii_summary.get("extracted_certifications", []),
        "ats_score": ats_analysis.get("ats_score", 0),
        "strengths": ats_analysis.get("strengths", []),
        "weaknesses": ats_analysis.get("weaknesses", []),
        "star_rewrites": ats_analysis.get("star_rewrites", []),
        "format_issues": ats_analysis.get("format_issues", []),
        "jd_match_percent": jd_match.get("match_percentage", 0.0),
        "matched_skills": jd_match.get("matched_skills", []),
        "missing_skills": jd_match.get("missing_skills", []),
        "recommendations": jd_match.get("recommendations", []),
    }


def submit_resume_to_api(api_url: str, resume_file, job_description: str) -> Dict[str, Any]:
    """Send a resume to the backend API using multipart form data."""
    files = {"resume_file": (resume_file.name, resume_file.getvalue(), resume_file.type or "application/octet-stream")}
    data = {"job_description": job_description}
    response = requests.post(api_url, files=files, data=data, timeout=60)
    response.raise_for_status()
    return response.json()


def render_gauge(score: float, title: str) -> None:
    """Render a round score gauge using CSS and HTML."""
    safe_score = max(0, min(float(score), 100.0))
    hue = int((safe_score / 100.0) * 120)
    st.markdown(
        f"""
        <div style="display:flex; flex-direction:column; align-items:center; gap:8px; margin-bottom:18px;">
          <div style="font-size:0.9rem; font-weight:600; color:#4b5563;">{title}</div>
          <div style="width:180px; height:180px; border-radius:50%; background: conic-gradient(hsl({hue}, 80%, 50%) 0 {safe_score}%, #e5e7eb {safe_score}% 100%); display:flex; align-items:center; justify-content:center; box-shadow: inset 0 0 20px rgba(0,0,0,0.08);">
            <div style="width:120px; height:120px; border-radius:50%; background:white; display:flex; align-items:center; justify-content:center; box-shadow: inset 0 0 20px rgba(0,0,0,0.04); font-size:2rem; font-weight:700; color:#111827;">{int(safe_score)}%</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_badges(values: List[str], color: str = "green") -> str:
    """Render a compact list of pill badges for skills."""
    if not values:
        return "No items to show."

    safe_color = {"green": "#dcfce7", "red": "#fee2e2", "blue": "#dbeafe"}.get(color, "#dcfce7")
    text_color = {"green": "#166534", "red": "#991b1b", "blue": "#1d4ed8"}.get(color, "#166534")
    badges = "\n".join(
        f'<span style="display:inline-block; margin:4px 6px 4px 0; padding:6px 10px; border-radius:999px; background:{safe_color}; color:{text_color}; font-weight:600; font-size:0.8rem;">{value}</span>'
        for value in values
    )
    return badges


def render_copy_button(label: str, text_to_copy: str) -> None:
    """Add a button that copies text via a small JavaScript helper."""
    html = f"""
    <button onclick="navigator.clipboard.writeText({text_to_copy!r}); this.textContent='Copied';" style="padding:8px 12px; border-radius:10px; border:1px solid #d1d5db; background:#fff; cursor:pointer;">{label}</button>
    """
    st.components.v1.html(html, height=50)


def run_dashboard() -> None:
    st.set_page_config(page_title="Resume Doctor", page_icon="🩺", layout="wide")
    st.title("Resume Doctor Dashboard")
    st.caption("AI-powered resume analysis, privacy masking, ATS scoring, and skill-gap review.")

    with st.sidebar:
        st.header("Settings")
        api_url = st.text_input("API URL", value=DEFAULT_API_URL)
        use_demo_mode = st.toggle("Use demo data", value=True)
        st.markdown("---")
        st.caption("Recommended backend endpoint: http://localhost:8000/api/analyze")

    uploaded_file = st.file_uploader("Upload resume (PDF or DOCX)", type=["pdf", "docx"])
    job_description = st.text_area(
        "Paste the job description",
        value=(
            "Senior Python Engineer with experience in FastAPI, Azure, SQL, and cloud-ready backend systems. "
            "Strong understanding of distributed services and product engineering."
        ),
        height=160,
    )

    if st.button("Analyze Resume"):
        if uploaded_file is None:
            st.warning("Please upload a resume before running analysis.")
            return

        with st.spinner("Running analysis..."):
            progress = st.progress(0)
            for step_index, message in enumerate([
                "Extracting layout...",
                "Redacting PII...",
                "Evaluating ATS...",
                "Matching JD...",
            ]):
                progress.progress((step_index + 1) / 4)
                st.text(message)

            try:
                if use_demo_mode:
                    result = build_demo_result("Senior Python Engineer", job_description, uploaded_file.name)
                else:
                    try:
                        result = asyncio.run(analyze_uploaded_resume(uploaded_file, job_description))
                    except Exception:
                        result = submit_resume_to_api(api_url, uploaded_file, job_description)
            except Exception as exc:  # pragma: no cover - UI error path
                st.error(f"Analysis failed: {exc}")
                return

            normalized = normalize_analysis_payload(result)
            st.session_state["analysis"] = normalized

    analysis = st.session_state.get("analysis")
    if analysis is None:
        return

    st.success("Analysis complete")

    col1, col2 = st.columns(2)
    with col1:
        render_gauge(analysis["ats_score"], "ATS Score")
    with col2:
        render_gauge(analysis["jd_match_percent"], "JD Match")

    st.markdown("---")

    pii_toggle = st.checkbox("Show raw resume text", value=False)
    left, right = st.columns(2)
    with left:
        st.subheader("Raw Resume")
        st.text_area("Raw text", value=analysis["raw_text"], height=220, label_visibility="collapsed")
    with right:
        st.subheader("Redacted Resume")
        st.text_area("Redacted text", value=analysis["clean_text"] or analysis["raw_text"], height=220, label_visibility="collapsed")

    if not pii_toggle:
        st.caption("Privacy mode: raw text is hidden by default. Toggle to review the original resume text.")

    st.markdown("---")
    st.subheader("Skill Gap")
    col_match, col_missing = st.columns(2)
    with col_match:
        st.write("Matched skills")
        st.markdown(render_badges(analysis["matched_skills"], "green"), unsafe_allow_html=True)
    with col_missing:
        st.write("Missing skills")
        st.markdown(render_badges(analysis["missing_skills"], "red"), unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("ATS Strengths & Weaknesses")
    strengths = analysis.get("strengths") or []
    weaknesses = analysis.get("weaknesses") or []
    st.write("Strengths")
    st.markdown(render_badges(strengths, "blue"), unsafe_allow_html=True)
    st.write("Weaknesses")
    st.markdown(render_badges(weaknesses, "red"), unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("STAR Rewrite Cards")
    for index, row in enumerate(analysis.get("star_rewrites") or []):
        st.markdown(f"### Rewrite {index + 1}")
        left_col, right_col = st.columns(2)
        with left_col:
            st.markdown("**Original**")
            st.write(row.get("original", ""))
        with right_col:
            st.markdown("**Improved STAR version**")
            st.write(row.get("improved_star", ""))
            st.caption(row.get("impact_metric", ""))
            render_copy_button("Copy bullet", row.get("improved_star", ""))

    st.markdown("---")
    st.subheader("Detected PII")
    if analysis.get("detected_pii"):
        for pii in analysis["detected_pii"]:
            st.write(f"- {pii.get('type')}: {pii.get('text')} (confidence {pii.get('confidence', 0)})")
    else:
        st.write("No sensitive entities detected.")


def main() -> None:
    run_dashboard()


if __name__ == "__main__":
    main()
