"""Vercel serverless function entry point.

Exposes the FastAPI ASGI app so Vercel's Python runtime can serve it.
All /api/* requests are routed here via vercel.json rewrites.
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path so "backend", "shared", etc. resolve
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from backend.api import app  # noqa: E402, F401
