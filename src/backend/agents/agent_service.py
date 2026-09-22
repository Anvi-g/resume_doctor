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
        from azure.ai.projects.models import (
            AgentEndpointConfig,
            FixedRatioVersionSelectionRule,
            PromptAgentDefinition,
            ProtocolConfiguration,
            ResponsesProtocolConfiguration,
            VersionSelector,
        )
        from azure.identity import DefaultAzureCredential

        if not self.is_configured:
            raise RuntimeError("Azure AI Foundry Agent Service is not configured (missing endpoint or FORCE_OFFLINE=1).")

        credential = DefaultAzureCredential()
        self._project_client = AIProjectClient(
            endpoint=self.endpoint,
            credential=credential,
            allow_preview=True,
        )

        # --- Preferred mode: register the agent in the Foundry project ---
        try:
            definition = PromptAgentDefinition(
                model=self.model,
                instructions=SUPERVISOR_INSTRUCTIONS,
                tools=build_tool_definitions(),
            )
            version = self._project_client.agents.create_version(
                agent_name=self.agent_name,
                definition=definition,
                description="Resume Doctor supervisor agent (4 Azure AI-103 module tools)",
            )
            endpoint_config = AgentEndpointConfig(
                version_selector=VersionSelector(
                    version_selection_rules=[
                        FixedRatioVersionSelectionRule(agent_version=version.version, traffic_percentage=100)
                    ]
                ),
                protocol_configuration=ProtocolConfiguration(responses=ResponsesProtocolConfiguration()),
            )
            try:
                self._project_client.agents.update_details(agent_name=self.agent_name, agent_endpoint=endpoint_config)
            except Exception as exc:  # pragma: no cover - endpoint feature may be disabled
                logger.warning("Agent endpoint update failed (%s); falling back to plain responses path.", exc)
                raise
            self._openai_client = self._project_client.get_openai_client(agent_name=self.agent_name)
            self.mode = "agent_service"
            logger.info("Agent '%s' version %s registered and endpoint configured.", self.agent_name, version.version)
        except Exception as exc:
            self._agent_error = str(exc)
            logger.warning("Agent Service mode unavailable (%s). Using plain Foundry responses path.", exc)
            try:
                self._openai_client = self._project_client.get_openai_client()
                self.mode = "responses"
            except Exception as exc2:  # pragma: no cover
                self._agent_error = str(exc2)
                logger.error("Unable to create a Foundry OpenAI client: %s", exc2)
                self._openai_client = None

    # ------------------------------------------------------------------
    # Public async API (used by FastAPI routes)
    # ------------------------------------------------------------------
    async def analyze(self, file_bytes: bytes, filename: str, job_description: str = "", target_role: str = "") -> MasterAnalyzeResponse:
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
            raise RuntimeError(f"Azure Agent Service unavailable: {self._agent_error}")

        return await asyncio.to_thread(
            self._run_agent_sync,
            file_bytes,
            filename,
            job_description,
            target_role,
        )

    # ------------------------------------------------------------------
    # Sync agent loop (executed in a worker thread)
    # ------------------------------------------------------------------
    def _run_agent_sync(self, file_bytes: bytes, filename: str, job_description: str, target_role: str) -> MasterAnalyzeResponse:
        ctx = self.tool_context_factory()
        ctx.file_bytes = file_bytes
        ctx.filename = filename
        ctx.target_jd = job_description
        ctx.target_role = target_role

        user_prompt = self._build_user_prompt(filename, job_description, target_role)
        tool_specs = build_tool_specs_raw()

        self.last_run_trace = []
        self.last_agent_summary = ""

        response = self._openai_client.responses.create(
            model=self.model,
            instructions=SUPERVISOR_INSTRUCTIONS,
            input=[{"role": "user", "content": user_prompt}],
            tools=tool_specs,
            parallel_tool_calls=False,
        )
        previous_response_id = response.id
        tool_outputs: Dict[str, Dict[str, Any]] = {}

        for _turn in range(MAX_AGENT_TURNS):
            function_inputs: List[FunctionCallOutput] = []
            pending_calls = [
                (item.name, item.call_id, item.arguments)
                for item in response.output
                if item.type == "function_call"
            ]
            if not pending_calls:
                break

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
            previous_response_id = response.id

        self.last_agent_summary = getattr(response, "output_text", "") or ""

        if "parse_resume" not in tool_outputs:
            raise RuntimeError("Agent did not call parse_resume; cannot produce a document summary.")

        ats = tool_outputs.get("score_ats", {})
        jd = tool_outputs.get("match_jd", {})
        pii = tool_outputs.get("redact_pii", {})
        star_rewrites = ats.get("star_rewrites", [])

        if not jd:
            jd = {
                "match_percentage": 0.0,
                "matched_skills": [],
                "missing_skills": [],
                "recommendations": ["Agent did not run the JD matcher."],
                "cosine_similarity": 0.0,
                "skill_match_ratio": 0.0,
            }

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