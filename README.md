# Resume Doctor — Agentic Edition (Azure AI-103)

A genuinely **agentic** rewrite of the AI-103 "Resume Doctor" lab. Instead of a
hand-wired Python pipeline (`asyncio.gather`), an **Azure AI Foundry Agent Service
supervisor agent** decides at runtime which of the 4 module **worker functions** to
call, in which order, and assembles the final `MasterAnalyzeResponse`.

```
 ┌───────────────────────────────────────────────────────────────┐
 │  Azure AI Foundry Agent Service (supervisor agent)            │
 │  model: gpt-4.1-mini, name: resume-doctor                     │
 │  decides tool call order itself at runtime                    │
 └───────────────┬───────────────────────────────────────────────┘
                 │  OpenAI Responses loop (function tools)
        ┌────────┴────────┬──────────────┬───────────────┐
        ▼                 ▼              ▼               ▼
  parse_resume      redact_pii       score_ats       match_jd
  (DocIntel)      (AI Language)   (Azure OpenAI)   (TF-IDF+Cosine)
```

Resume bytes live on a per-request `ToolContext` (the agent passes only JSON args,
so tools receive the filename; offline mock always works with zero Azure keys).

## Repo layout

| Path | Purpose |
|---|---|
| `src/backend/agents/function_tools.py` | 4 module tool functions + OpenAI `FunctionTool` definitions + dispatcher |
| `src/backend/agents/agent_service.py` | Supervisor-agent Responsive loop, 3-mode fallback, trace capture |
| `src/backend/orchestrator.py` | Deterministic `MasterOrchestrator` — kept as the **offline fallback** |
| `src/backend/app.py` | FastAPI gateway; `/api/analyze` now routes through the agent |
| `tests/test_agent.py` | Agent loop harness (scripted, no network) + opt-in LIVE test |

## Modes

| Mode | Trigger | What runs |
|---|---|---|
| **agent_service** | `AZURE_AI_PROJECT_ENDPOINT` set, `FORCE_OFFLINE=0` | Foundry agent service + Responses function-tool loop |
| **responses** (stateless) | agent platform fails at runtime | `get_openai_client()` + tools passed per request |
| **offline** | endpoint unset or `FORCE_OFFLINE=1` | `MasterOrchestrator` (deterministic, no Azure needed) |

`GET /api/agent/trace` returns the last run's tool-call order + agent summary
(useful for the demo deck: *"the agent chose parse → redact → score → match"*).

## Run offline (0 Azure keys)

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
FORCE_OFFLINE=1 uvicorn src.backend.main:app --reload --port 8000
```

```bash
curl -s -F "file=@tests/sample_resumes/sample_resume_testing.pdf" \
     -F "job_description=Python Developer with FastAPI, Docker, Azure, Git and PostgreSQL." \
     http://localhost:8000/api/analyze | python -m json.tool
curl -s http://localhost:8000/api/agent/trace | python -m json.tool
```

## Enable the live supervisor agent

1. **Provision** an Azure AI Foundry project: sign in at `ai.azure.com`, create a
   project (hub), and deploy a chat model (e.g. `gpt-4.1-mini`).
2. Copy `.env.example` → `.env` and set `AZURE_AI_PROJECT_ENDPOINT` (project
   **Overview → Project endpoint**) and `AZURE_AI_MODEL_DEPLOYMENT_NAME`.
3. Provide the same-scope keys for the three AI service tools
   (`AZURE_DOC_INTEL_*`, `AZURE_AI_LANG_*`, `AZURE_OPENAI_*`).
4. Authenticate with
   [`DefaultAzureCredential`](https://learn.microsoft.com/en-us/python/api/azure-identity/azure.identity.defaultazurecredential)
   — `az login` (Azure CLI) works out of the box; set the right subscription/target the project.
5. Start the server. On the first request the supervisor agent is registered on
   the platform and drives the tools. Watch the order in `/api/agent/trace`.

## Tests

```bash
# hermetic offline suite (no Azure keys required)
venv/bin/pytest -q

# live integration — only when a real project endpoint is available
export AZURE_AI_PROJECT_ENDPOINT=https://<your-project>.eastus2.aiservices.azure.com/
az login
venv/bin/pytest -q -m slow
```

51 tests cover the 4 worker tools offline, the agent loop (scripted fake client),
deterministic assembly, and the FastAPI gateway.

## Responsible AI

See `docs/responsible_ai.md` for the fairness/transparency notes that ship with
this lab edition.