"""
FastAPI Entrypoint alias for Resume Doctor Gateway
Allows running with:
    uvicorn src.backend.main:app --reload --port 8000
"""

from src.backend.app import app

__all__ = ["app"]
