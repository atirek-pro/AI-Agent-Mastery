"""
observability.py
================
Everything related to tracing (Arize + OpenInference) lives here.

Two responsibilities:

1. `using_prompt_template` - a context manager that records the prompt template
   (and its variables) on the current span. If the OpenInference packages are
   not installed we fall back to a no-op so callers never need a try/except.
2. `init_tracing()` - call once at app startup to register the Arize tracer and
   instrument LangChain, LiteLLM and (optionally) MCP.
"""

from __future__ import annotations

import os

from config import ARIZE_PROJECT_NAME, ENABLE_MCP

# ---------------------------------------------------------------------------
# Optional imports - tracing must never be the reason the app fails to boot.
# ---------------------------------------------------------------------------
try:  # pragma: no cover - depends on the local environment
    from arize.otel import register
    from openinference.instrumentation.langchain import LangChainInstrumentor
    from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor
    from openinference.instrumentation import using_prompt_template

    TRACING_AVAILABLE = True
except Exception:  # pragma: no cover
    TRACING_AVAILABLE = False

    def using_prompt_template(**kwargs):  # type: ignore[misc]
        """No-op replacement when OpenInference is unavailable."""
        from contextlib import contextmanager

        @contextmanager
        def _noop():
            yield

        return _noop()


def init_tracing() -> bool:
    """Register the Arize tracer and instrument the frameworks we use.

    Safe to call unconditionally: returns False (and does nothing) when tracing
    is unavailable or the credentials are missing.

    Returns
    -------
    bool
        True if tracing was successfully configured.
    """
    if not TRACING_AVAILABLE:
        return False

    space_id = os.getenv("ARIZE_SPACE_ID")
    api_key = os.getenv("ARIZE_API_KEY")
    if not (space_id and api_key):
        return False

    try:
        tracer_provider = register(
            space_id=space_id,
            api_key=api_key,
            project_name=ARIZE_PROJECT_NAME,
        )
        # LangChain/LangGraph spans (chains, agents, tools).
        LangChainInstrumentor().instrument(
            tracer_provider=tracer_provider,
            include_chains=True,
            include_agents=True,
            include_tools=True,
        )
        # Raw Google GenAI calls (Gemini), used by ChatGoogleGenerativeAI and
        # GoogleGenerativeAIEmbeddings under the hood.
        GoogleGenAIInstrumentor().instrument(tracer_provider=tracer_provider)

        if ENABLE_MCP:
            from openinference.instrumentation.mcp import MCPInstrumentor

            MCPInstrumentor().instrument(tracer_provider=tracer_provider)

        return True
    except Exception:
        # Tracing is best-effort: never break the request path over it.
        return False