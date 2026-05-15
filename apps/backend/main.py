"""Monorepo entry point: exposes the FastAPI app as ``main:app`` so the shared
Aplhion dev/start scripts (``uvicorn main:app``) work unchanged. Backend imports
are absolute against the top-level packages beside this file; both script
invocation styles (cd apps/backend / --app-dir apps/backend) put this dir on
sys.path. The explicit insert is belt-and-suspenders (mirrors api/index.py)."""
import sys
from pathlib import Path

_backend_root = str(Path(__file__).resolve().parent)
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)

from backend.api import app  # noqa: E402,F401

__all__ = ["app"]
