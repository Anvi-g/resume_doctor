"""
Tests for the Azure AI-103 supervisor agent layer.

Covers:
1. Tool registry: 4 module FunctionTools with correct signatures.
2. Each module tool executes and returns its JSON contract offline.
3. Deterministic result assembly after a simulated agent tool loop.
4. Offline fallback to the deterministic orchestrator.
5. Optional LIVE integration test against the Foundry Agent Service
   (runs only when AZURE_AI_PROJECT_ENDPOINT is set in the shell).
"""

import os
import asyncio
import json
import pytest

from src.backend.models.schemas import MasterAnalyzeResponse
from src.backend.agents.agent_service import ResumeDoctorAgentService, agent_service
from src.backend.agents.function_tools import (
    build_default_context,
    build_tool_definitions,
    build_tool_specs_raw,
    execute_tool,
    _extract_candidate_bullets,
)

PDF_PATH = os.path.join(os.path.dirname(__file__), "sample_resumes", "sample_resume_testing.pdf")
SAMPLE_JD = "Python Developer with FastAPI, Docker, Azure, Git and PostgreSQL."


def _pdf_bytes() -> bytes:
    with open(PDF_PATH, "rb") as fh:
        return fh.read()


# =====================================================================
# 1. Tool registry
# =====================================================================
def test_four_module_tools_registered():
    tools = build_tool_definitions()
    assert [t.name for t in tools] == ["parse_resume", "redact_pii", "score_ats", "match_jd"]
    for tool in tools:
        params = tool.parameters
        assert params["type"] == "object"
        assert params.get("required"), f"{tool.name} missing required args"


def test_raw_specs_are_openai_compatible():
    specs = build_tool_specs_raw()
    assert len(specs) == 4
    assert all(s["type"] == "function" and "parameters" in s for s in specs)


# =====================================================================
# 2. Module tool execution (offline)
# =====================================================================
def test_execute_parse_resume_tool():
    ctx = build_default_context()
    ctx.file_bytes = _pdf_bytes()
    ctx.filename = "sample_resume_testing.pdf"
    out = execute_tool("parse_resume", {"filename": ctx.filename}, ctx)
    assert isinstance(out, dict)
    assert out.get("file_type") == "pdf"
    assert len(out.get("raw_text", "")) > 0


def test_execute_redact_pii_tool():
    ctx = build_default_context()
    text = "Contact jane.smith@domain.org or +1 (555) 234-5678. Python and Docker expert."
    out = execute_tool("redact_pii", {"text": text}, ctx)
    assert "jane.smith@domain.org" not in out["clean_text"]
    assert "[EMAIL]" in out["clean_text"]
    assert "Python" in out["extracted_skills"]
    assert "Docker" in out["extracted_skills"]


def test_execute_score_ats_tool():
    ctx = build_default_context()
    resume = (
        "Experienced Python developer.\n"
        "- Built scalable REST APIs with FastAPI and Docker.\n"
        "- Reduced backend latency by 35% with async caching.\n"
        "Skills: Python, FastAPI, Docker, SQL, Azure."
    )
    out = execute_tool("score_ats", {"resume_text": resume, "target_jd": SAMPLE_JD}, ctx)
    assert "overall_score" in out
    assert 0 <= out["overall_score"] <= 100
    assert isinstance(out.get("star_rewrites"), list)


def test_execute_match_jd_tool():
    ctx = build_default_context()
    clean = "Experienced Python backend engineer proficient in FastAPI, Docker, Git, and PostgreSQL."
    out = execute_tool(
        "match_jd",
        {"clean_text": clean, "jd_text": SAMPLE_JD, "resume_skills": ["Python", "FastAPI", "Docker", "PostgreSQL"]},
        ctx,
    )
    assert out["match_percentage"] >= 0.0
    assert "Python" in out["matched_skills"]


def test_extract_candidate_bullets_skips_contacts():
    clean = (
        "Email: a@b.com\n"
        "- Built a web application for managing tasks with authentication.\n"
        "- Engineered high-concurrency FastAPI REST endpoints.\n"
        "- Reduced preprocessing latency by 70% for ML backends.\n"
        "Summary:\n"
    )
    bullets = _extract_candidate_bullets(clean)
    assert len(bullets) == 3
    assert all("@" not in b for b in bullets)


# =====================================================================
# 3. Agent loop + deterministic assembly (simulated, no network)
# =====================================================================
class _FakeResponse:
    def __init__(self, output, rid="resp_1", output_text="done"):
        self.output = output
        self.id = rid
        self.output_text = output_text


class _FakeCall:
    def __init__(self, name, args, call_id):
        self.type = "function_call"
        self.name = name
        self.arguments = json.dumps(args)
        self.call_id = call_id


class _FakeResponses:
    """Scripted responses.create callback used to drive the agent loop offline."""

    def __init__(self, script):
        self._script = list(script)
        self.calls = []

    def create(self, **_):
        self.calls.append(_)
        return self._script.pop(0)


def test_agent_loop_runs_all_four_tools_and_assembles():
    svc = ResumeDoctorAgentService()
    script = [
        _FakeResponse(
            output=[
                _FakeCall("parse_resume", {"filename": "sample.pdf"}, "call_1"),
                _FakeCall("redact_pii", {"text": "Python developer at ACME. Email a@b.com"}, "call_2"),
            ],
            rid="resp_1",
        ),
        _FakeResponse(
            output=[
                _FakeCall("score_ats", {"resume_text": "Python developer.", "target_jd": SAMPLE_JD}, "call_3"),
                _FakeCall(
                    "match_jd",
                    {"clean_text": "Python developer.", "jd_text": SAMPLE_JD, "resume_skills": ["Python"]},
                    "call_4",
                ),
            ],
            rid="resp_2",
        ),
        _FakeResponse(output=[], rid="resp_3", output_text="ATS score 83, match 50%."),
    ]
    svc._openai_client = type("C", (), {"responses": _FakeResponses(script)})()

    result = svc._run_agent_sync(_pdf_bytes(), "sample.pdf", SAMPLE_JD, "Python Backend")

    assert isinstance(result, MasterAnalyzeResponse)
    tool_names = [t["tool"] for t in svc.last_run_trace]
    assert tool_names[:4] == ["parse_resume", "redact_pii", "score_ats", "match_jd"]
    assert list(result.model_dump().keys()) == [
        "doc_summary", "pii_summary", "ats_analysis", "jd_match", "star_bullet_rewrites",
    ]
    assert result.doc_summary.get("file_type") == "pdf"
    assert result.ats_analysis.get("overall_score", 0) >= 0


def test_agent_loop_errors_when_parse_not_called():
    svc = ResumeDoctorAgentService()
    script = [
        _FakeResponse(output=[_FakeCall("score_ats", {"resume_text": "x"}, "c1")], rid="resp_1"),
        _FakeResponse(output=[], rid="resp_2"),
    ]
    svc._openai_client = type("C", (), {"responses": _FakeResponses(script)})()
    with pytest.raises(RuntimeError, match="parse_resume"):
        svc._run_agent_sync(_pdf_bytes(), "sample.pdf", SAMPLE_JD, "")


# =====================================================================
# 4. Offline fallback
# =====================================================================
def test_offline_fallback_returns_master_response():
    assert agent_service.mode == "offline"
    assert agent_service.is_configured is False

    result = asyncio.run(agent_service.analyze(_pdf_bytes(), "sample.pdf", SAMPLE_JD, "Python Backend"))
    assert isinstance(result, MasterAnalyzeResponse)
    assert result.jd_match.match_percentage >= 0.0
    assert result.ats_analysis.get("overall_score", 0) > 0


# =====================================================================
# 5. LIVE integration (opt-in)
# =====================================================================
@pytest.mark.skipif(
    not os.environ.get("AZURE_AI_PROJECT_ENDPOINT"),
    reason="Set AZURE_AI_PROJECT_ENDPOINT to run the live Agent Service test",
)
@pytest.mark.slow
def test_live_agent_analyze():
    svc = ResumeDoctorAgentService()
    svc.is_configured = True
    svc._ensure_connected()
    assert svc._openai_client is not None

    result = asyncio.run(svc.analyze(_pdf_bytes(), "sample_resume_testing.pdf", SAMPLE_JD, "Python Backend"))
    assert isinstance(result, MasterAnalyzeResponse)
    assert len(svc.last_run_trace) >= 4
    assert svc.last_agent_summary.strip() != ""