"""
pytest configuration and shared fixtures.

Adds the relevant directories to sys.path so tests can import:
  - dataObjectQueryService.*   (service layer package)
  - server                     (openapi-tool-server FastAPI app)
"""
import os
import sys

import pytest

# ---------------------------------------------------------------------------
# Path setup — must happen before any project imports
# ---------------------------------------------------------------------------
_REPO_ROOT    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SERVICES_DIR = os.path.join(_REPO_ROOT, "src", "services")
_API_DIR      = os.path.join(_REPO_ROOT, "src", "openapi-tool-server")

for _path in (_SERVICES_DIR, _API_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)
