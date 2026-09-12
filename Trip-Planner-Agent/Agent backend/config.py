"""
config.py
=========
Single place where the environment is read.

Why this file exists
--------------------
Before decoupling, every module called `os.getenv(...)` on its own. That makes it
hard to know which flags the app honours. Now:

    from config import ENABLE_RAG, LOCAL_GUIDES_PATH

is the only way the rest of the codebase touches configuration.

It also owns `.env` loading, so as long as something imports `config` first
(which everything does), the environment is ready.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv, find_dotenv

# ---------------------------------------------------------------------------
# Environment: load .env as early as possible, before any flag below is read.
# ---------------------------------------------------------------------------
load_dotenv(find_dotenv())

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent          # .../Agent backend
DATA_DIR = BASE_DIR / "data"                        # curated datasets live here
LOCAL_GUIDES_PATH = DATA_DIR / "local_guides.json"  # RAG corpus for local guides


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def env_flag(name: str, default: str = "0") -> bool:
    """Parse a boolean-ish environment variable.

    Anything other than "0" / "false" / "no" counts as enabled, so both
    `ENABLE_RAG=true` and `ENABLE_RAG=1` work.
    """
    return os.getenv(name, default).lower() not in {"0", "false", "no"}


# ---------------------------------------------------------------------------
# Optional dependency detection
# ---------------------------------------------------------------------------
# MCP instrumentation is optional: the demo still runs without it installed.
try:  # pragma: no cover - depends on the local environment
    from openinference.instrumentation.mcp import MCPInstrumentor  # noqa: F401

    MCP_INSTRUMENTATION_AVAILABLE = True
except ImportError:  # pragma: no cover
    MCP_INSTRUMENTATION_AVAILABLE = False


# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------
# TEST_MODE swaps the real LLM for a deterministic stub (used by smoke tests).
IS_TEST_MODE = bool(os.getenv("TEST_MODE"))

# RAG is on by default; MCP is opt-in and only possible if the package exists.
ENABLE_RAG = env_flag("ENABLE_RAG", "1")
ENABLE_MCP = env_flag("ENABLE_MCP", "0") and MCP_INSTRUMENTATION_AVAILABLE

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------
# Timeout (seconds) for the third-party search APIs (Tavily / SerpAPI).
SEARCH_TIMEOUT = float(os.getenv("SEARCH_API_TIMEOUT", "8"))

# Embedding model used to build the in-memory vector index.
EMBED_MODEL = os.getenv("GOOGLE_EMBED_MODEL", "models/gemini-embedding-001")

# Arize project name used when tracing is configured.
ARIZE_PROJECT_NAME = os.getenv("ARIZE_PROJECT_NAME", "ai-trip-planner")