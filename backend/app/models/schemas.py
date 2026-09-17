"""
Alias/Wrapper module for backend/app/models/schemas.py.

This module re-exports all Pydantic data schemas from `src.backend.models.schemas`
to ensure full import path compatibility regardless of whether a service imports from
`src.backend.models.schemas` or `backend.app.models.schemas`.
"""

# Re-exporting all Pydantic models from primary schemas file
from src.backend.models.schemas import (
    ATSScoreOutput,          # Overall ATS evaluation model
    ATSCategoryBreakdown,    # 5-category score breakdown model
    STARRewriteItem,         # Individual STAR bullet transformation item model
    STARRewriteBatchOutput,  # Batch STAR bullet transformations model
    ATSScoreRequest,         # HTTP POST payload model for ATS scoring endpoint
    STARRewriteRequest,      # HTTP POST payload model for STAR rewrite endpoint
)

# Explicitly declare exported public symbols for wildcard imports (`from schemas import *`)
__all__ = [
    "ATSScoreOutput",
    "ATSCategoryBreakdown",
    "STARRewriteItem",
    "STARRewriteBatchOutput",
    "ATSScoreRequest",
    "STARRewriteRequest",
]
