"""
Alias/Wrapper module for backend/app/main.py.

This module re-exports the FastAPI app instance from `src.backend.app`
to guarantee full import compatibility across project layout standards:
- uvicorn src.backend.app:app
- uvicorn backend.app.main:app
"""

# Re-export FastAPI application instance from primary gateway file
from src.backend.app import app

# Explicit list of exported symbols
__all__ = ["app"]
