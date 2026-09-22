"""
Test bootstrap.

Keeps the unit suite hermetic: unless AZURE_AI_PROJECT_ENDPOINT is explicitly set
in the shell (live agent integration run), force the deterministic offline mode and
blank the three worker-service credentials so no Azure network calls are made during
normal `pytest` runs, regardless of what .env contains.
"""

import os

live = bool(os.environ.get("AZURE_AI_PROJECT_ENDPOINT"))

if not live:
    os.environ["FORCE_OFFLINE"] = "1"
    os.environ["AZURE_AI_PROJECT_ENDPOINT"] = ""
    for var in (
        "AZURE_DOC_INTEL_ENDPOINT", "AZURE_DOC_INTEL_KEY",
        "AZURE_AI_LANG_ENDPOINT", "AZURE_AI_LANG_KEY",
        "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_KEY",
    ):
        os.environ[var] = ""