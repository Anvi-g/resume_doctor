"""
Alias/Wrapper module for backend/app/main.py.

This module re-exports the FastAPI app instance from `src.backend.app`
to guarantee full import compatibility across project layout standards:
- uvicorn src.backend.app:app
- uvicorn backend.app.main:app
"""

import sys
from pathlib import Path

# Add project root directory to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Re-export FastAPI application instance from primary gateway file
from src.backend.app import app

# Explicit list of exported symbols
__all__ = ["app"]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

