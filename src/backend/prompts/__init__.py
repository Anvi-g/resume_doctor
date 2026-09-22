"""
Prompts Package Initializer.

This module exposes the system prompts and ChatPromptTemplates for ATS Scoring and STAR Bullet Rewriting
from `ats_prompts.py` for clean package imports.
"""

# Re-exporting prompt strings and ChatPromptTemplate objects
from src.backend.prompts.ats_prompts import (
    ATS_SCORING_SYSTEM_PROMPT,     # System prompt string for ATS scoring LLM chain
    ATS_SCORING_USER_TEMPLATE,       # User template string for ATS scoring LLM chain
    ATS_SCORING_PROMPT_TEMPLATE,     # LangChain ChatPromptTemplate object for ATS scoring
    STAR_REWRITE_SYSTEM_PROMPT,    # System prompt string for STAR bullet rewrite LLM chain
    STAR_REWRITE_USER_TEMPLATE,      # User template string for STAR bullet rewrite LLM chain
    STAR_REWRITE_PROMPT_TEMPLATE,    # LangChain ChatPromptTemplate object for STAR bullet rewrite
)

# Explicit list of exported symbols
__all__ = [
    "ATS_SCORING_SYSTEM_PROMPT",
    "ATS_SCORING_USER_TEMPLATE",
    "ATS_SCORING_PROMPT_TEMPLATE",
    "STAR_REWRITE_SYSTEM_PROMPT",
    "STAR_REWRITE_USER_TEMPLATE",
    "STAR_REWRITE_PROMPT_TEMPLATE",
]
