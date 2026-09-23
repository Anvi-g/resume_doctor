"""
Resume Doctor Supervisor Agent (Azure AI-103 Agent Service).

Replaces the deterministic ``asyncio.gather`` pipeline with a real agent: a GPT
model hosted on Azure OpenAI (connected to the Microsoft Foundry project) decides
which of the four module *FunctionTools* to call and in what order via the
OpenAI-compatible Responses API.

Run-style flow (stateless Responses chaining):
    1. ``responses.create`` with instructions + user prompt + 4 tool specs
    2. inspect output for ``function_call`` items, execute them locally
    3. feed ``function_call_output`` back via ``previous_response_id``
    4. repeat until the model emits no more tool calls

Two live authentication modes are supported:
    * agent_service — agent version created in the Foundry project and an agent
      endpoint is configured (preview capability, matches the official SDK sample)
    * responses     — plain Foundry model endpoint; tool specs passed per request
Offline (no ``AZURE_AI_PROJECT_ENDPOINT`` or ``FORCE_OFFLINE=1``) falls back to
the deterministic ``MasterOrchestrator`` so unit tests / grading run without cloud.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from openai.types.responses.response_input_param import FunctionCallOutput

from src.backend.config import settings
from src.backend.models.schemas import JDMatchResult, MasterAnalyzeResponse
from src.backend.orchestrator import MasterOrchestrator
from src.backend.agents.function_tools import (
    ToolContext,
    build_default_context,
    build_tool_definitions,
    build_tool_specs_raw,
    execute_tool,
)

logger = logging.getLogger(__name__)

# Maximum number of agent turns (tool-call rounds) before the loop gives up.
MAX_AGENT_TURNS = 8

SUPERVISOR_INSTRUCTIONS = """\
You are "Resume Doctor", a senior ATS recruiter that audits resumes using Azure \
AI-103 services. You have four tools mirroring four AI modules:
1. parse_resume  -> Azure AI Document Intelligence (extracts raw text + layout)
2. redact_pii    -> Azure AI Language (masks [NAME]/[EMAIL]/[PHONE] + extracts skills)
3. score_ats     -> Azure OpenAI (5-category ATS score + STAR bullet rewrites)
4. match_jd      -> TF-IDF cosine similarity + skill gap vs target job description

Execute the FULL pipeline for every resume, in dependency order (1 -> 2 -> 3 -> 4),
feeding the output of each call into the next tool's input. Do not stop early.
After all tools return, answer with a short natural-language summary of the resume
audit: overall ATS score, JD match %, top strengths and the biggest gaps.
"""


class ResumeDoctorAgentService:
    """Supervisor agent driving the four module function tools via Agent Service."""

    def __init__(self) -> None:
        self.endpoint = (settings.AZURE_AI_PROJECT_ENDPOINT or "").strip()
        self.model = (settings.AZURE_AI_MODEL_DEPLOYMENT_NAME or "").strip()
        self.agent_name = settings.AZURE_AGENT_NAME

        self.is_configured = bool(self.endpoint) and not settings.FORCE_OFFLINE
        self.mode: str = "offline"
        self._project_client = None
        self._openai_client: Optional[Any] = None
        self._agent_error: Optional[str] = None

        self.fallback_orchestrator = MasterOrchestrator()
        self.tool_context_factory = build_default_context

        self.last_run_trace: List[Dict[str, Any]] = []
        self.last_agent_summary: str = ""

        if self.is_configured:
            logger.info(
                "ResumeDoctorAgentService configured (endpoint=%s model=%s agent=%s)",
                self.endpoint,
                self.model,
                self.agent_name,
            )
            try:
                self._ensure_connected()
            except Exception as exc:
                logger.warning("Eager agent connection failed (%s); will retry on analyze().", exc)
        else:
            reason = "FORCE_OFFLINE=1" if settings.FORCE_OFFLINE else "no AZURE_AI_PROJECT_ENDPOINT set"
            logger.info("ResumeDoctorAgentService running OFFLINE (%s). Falling back to deterministic orchestrator.", reason)

    # ------------------------------------------------------------------
    # Lazy Azure client setup
    # ------------------------------------------------------------------
    def _ensure_connected(self) -> None:
        if self.mode in ("agent_service", "responses") or self._openai_client is not None:
            return

        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential

        if not self.is_configured:
            raise RuntimeError("Azure AI Foundry Agent Service is not configured (missing endpoint or FORCE_OFFLINE=1).")

        try:
            import concurrent.futures
            def _connect():
                credential = DefaultAzureCredential(
                    exclude_managed_identity_credential=True,
                    exclude_workload_identity_credential=True,
                    exclude_shared_token_cache_credential=True,
                    exclude_developer_cli_credential=True,
                )
                p_client = AIProjectClient(
                    endpoint=self.endpoint,
                    credential=credential,
                    allow_preview=True,
                )
                return p_client, p_client.get_openai_client()

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_connect)
                self._project_client, self._openai_client = future.result(timeout=2.0)

            self.mode = "agent_service" if self._project_client else "responses"
            logger.info("Foundry Agent Service client initialized successfully (mode=%s).", self.mode)
        except Exception as exc:
            self._agent_error = str(exc)
            logger.warning("Unable to create a Foundry OpenAI client: %s", exc)
            self._openai_client = None

    # ------------------------------------------------------------------
    # Public async API (used by FastAPI routes)
    # ------------------------------------------------------------------
    async def analyze(self, file_bytes: bytes, filename: str, job_description: str = "", target_role: str = "", enable_pii: bool = True) -> MasterAnalyzeResponse:
        if not self.is_configured:
            return await self.fallback_orchestrator.analyze_to_model(
                file_bytes=file_bytes,
                filename=filename,
                job_description=job_description,
                target_role=target_role,
            )
        if self._openai_client is None:
            self._ensure_connected()
        if self._openai_client is None:
            return await self.fallback_orchestrator.analyze_to_model(
                file_bytes=file_bytes,
                filename=filename,
                job_description=job_description,
                target_role=target_role,
            )

        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    self._run_agent_sync,
                    file_bytes,
                    filename,
                    job_description,
                    target_role,
                    enable_pii,
                ),
                timeout=60.0,
            )
        except Exception as exc:
            logger.warning("Cloud Agent run timed out or failed (%s). Falling back to deterministic orchestrator.", exc)
            return await self.fallback_orchestrator.analyze_to_model(
                file_bytes=file_bytes,
                filename=filename,
                job_description=job_description,
                target_role=target_role,
            )

    # ------------------------------------------------------------------
    # Sync agent loop (executed in a worker thread)
    # ------------------------------------------------------------------
    def _run_agent_sync(self, file_bytes: bytes, filename: str, job_description: str, target_role: str, enable_pii: bool = True) -> MasterAnalyzeResponse:
        ctx = self.tool_context_factory()
        ctx.file_bytes = file_bytes
        ctx.filename = filename
        ctx.target_jd = job_description
        ctx.target_role = target_role

        user_prompt = self._build_user_prompt(filename, job_description, target_role)
        tool_specs = build_tool_specs_raw()

        self.last_run_trace = []
        self.last_agent_summary = ""
        tool_outputs: Dict[str, Dict[str, Any]] = {}

        if self._openai_client:
            create_kwargs: Dict[str, Any] = {
                "model": self.model,
                "input": [{"role": "user", "content": user_prompt}],
                "parallel_tool_calls": False,
            }
            if self.mode != "agent_service":
                create_kwargs["instructions"] = SUPERVISOR_INSTRUCTIONS
                create_kwargs["tools"] = tool_specs

            try:
                response = self._openai_client.responses.create(**create_kwargs)
                previous_response_id = getattr(response, "id", "resp_0")

                for _turn in range(MAX_AGENT_TURNS):
                    output_items = getattr(response, "output", []) or []
                    pending_calls = [
                        (getattr(item, "name", ""), getattr(item, "call_id", ""), getattr(item, "arguments", ""))
                        for item in output_items
                        if getattr(item, "type", "") == "function_call"
                    ]
                    if not pending_calls:
                        break

                    function_inputs: List[FunctionCallOutput] = []
                    for name, call_id, arguments in pending_calls:
                        args = json.loads(arguments or "{}")
                        result = execute_tool(name, args, ctx)
                        tool_outputs[name] = result
                        self.last_run_trace.append({"tool": name, "arguments": args, "output": result})
                        function_inputs.append(
                            FunctionCallOutput(type="function_call_output", call_id=call_id, output=json.dumps(result))
                        )

                    response = self._openai_client.responses.create(
                        model=self.model,
                        input=list(function_inputs),
                        previous_response_id=previous_response_id,
                    )
                    previous_response_id = getattr(response, "id", previous_response_id)

                self.last_agent_summary = getattr(response, "output_text", "") or ""
                agent_loop_ok = True
            except Exception as exc:
                agent_loop_ok = False
                logger.warning("Agent Responses loop encountered exception (%r); executing fallback pipeline.", exc)

        if "parse_resume" not in tool_outputs:
            if self._openai_client and agent_loop_ok:
                raise RuntimeError("Agent did not call parse_resume; cannot produce a document summary.")
            p_res = execute_tool("parse_resume", {"file_bytes": file_bytes, "filename": filename}, ctx)
            tool_outputs["parse_resume"] = p_res
            self.last_run_trace.append({"tool": "parse_resume", "arguments": {"filename": filename}, "output": p_res})

        # Ensure remaining tools executed if not called by agent loop
        if "redact_pii" not in tool_outputs or not enable_pii:
            raw_text = tool_outputs["parse_resume"].get("raw_text", "")
            r_res = execute_tool("redact_pii", {"text": raw_text}, ctx)
            if not enable_pii:
                r_res["clean_text"] = raw_text
                r_res["detected_pii"] = [{"type": "PII Masking", "text": "Disabled via UI Toggle Switch", "confidence": 1.0}]
            tool_outputs["redact_pii"] = r_res
            self.last_run_trace.append({"tool": "redact_pii", "arguments": {"text": "[RAW_TEXT]"}, "output": r_res})

        if "score_ats" not in tool_outputs:
            clean_text = tool_outputs["redact_pii"].get("clean_text", "")
            s_res = execute_tool("score_ats", {"resume_text": clean_text, "target_jd": job_description}, ctx)
            tool_outputs["score_ats"] = s_res
            self.last_run_trace.append({"tool": "score_ats", "arguments": {"resume_text": "[CLEAN_TEXT]", "target_jd": job_description}, "output": s_res})

        if "match_jd" not in tool_outputs:
            clean_text = tool_outputs["redact_pii"].get("clean_text", "")
            skills = tool_outputs["redact_pii"].get("extracted_skills", [])
            m_res = execute_tool("match_jd", {"clean_text": clean_text, "jd_text": job_description, "resume_skills": skills}, ctx)
            tool_outputs["match_jd"] = m_res
            self.last_run_trace.append({"tool": "match_jd", "arguments": {"clean_text": "[CLEAN_TEXT]", "jd_text": job_description, "resume_skills": skills}, "output": m_res})

        ats = tool_outputs.get("score_ats", {})
        jd = tool_outputs.get("match_jd", {})
        pii = tool_outputs.get("redact_pii", {})
        star_rewrites = ats.get("star_rewrites", [])

        return MasterAnalyzeResponse(
            doc_summary=tool_outputs["parse_resume"],
            pii_summary=pii,
            ats_analysis=ats,
            jd_match=JDMatchResult(**jd),
            star_bullet_rewrites={
                "rewrites": star_rewrites,
                "overall_summary": "STAR bullet transformations produced by the Resume Doctor agent.",
            },
        )

    @staticmethod
    def _build_user_prompt(filename: str, job_description: str, target_role: str) -> str:
        parts = [f"Please audit the uploaded resume file '{filename}' using all four tools."]
        if target_role:
            parts.append(f"Target role: {target_role}.")
        if job_description:
            parts.append(f"Target job description:\n{job_description}")
        else:
            parts.append("No job description provided — evaluate ATS quality only and then call match_jd with an empty JD.")
        parts.append("Return a concise executive summary after the tools complete.")
        return "\n".join(parts)

    def status(self) -> Dict[str, Any]:
        return {
            "configured": self.is_configured,
            "mode": self.mode,
            "agent_name": self.agent_name,
            "model": self.model,
            "error": self._agent_error,
            "last_tool_calls": self.last_run_trace,
        }


# Module-level singleton for reuse across the FastAPI app.
agent_service = ResumeDoctorAgentService()