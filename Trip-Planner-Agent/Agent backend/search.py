"""
search.py
=========
Web-search access plus the small text helpers the tools rely on.

Two providers are supported and tried in order: Tavily, then SerpAPI. If neither
is configured (or both fail) callers get `None` and are expected to fall back to
the LLM.
"""

from __future__ import annotations

import os
from typing import Optional

import httpx
from langchain_core.messages import HumanMessage, SystemMessage

from config import SEARCH_TIMEOUT
from llm import llm


def compact(text: str, limit: int = 200) -> str:
    """Collapse whitespace and truncate on a word boundary.

    Tool results are fed straight back into the model, so keeping them short and
    tidy keeps prompts (and costs) predictable.
    """
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    truncated = cleaned[:limit].rstrip()
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated.rstrip(",.;- ")


def search_api(query: str) -> Optional[str]:
    """Run `query` against the configured search provider.

    Returns a compact summary string, or None if no provider is configured or
    the request failed.
    """
    query = query.strip()
    if not query:
        return None

    # --- Provider 1: Tavily -------------------------------------------------
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        try:
            with httpx.Client(timeout=SEARCH_TIMEOUT) as client:
                resp = client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": tavily_key,
                        "query": query,
                        "max_results": 3,
                        "search_depth": "basic",
                        "include_answer": True,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                answer = data.get("answer") or ""
                snippets = [
                    item.get("content") or item.get("snippet") or ""
                    for item in data.get("results", [])
                ]
                combined = " ".join([answer] + snippets).strip()
                if combined:
                    return compact(combined)
        except Exception:
            # Swallow and try the next provider; search is best-effort.
            pass

    # --- Provider 2: SerpAPI ------------------------------------------------
    serp_key = os.getenv("SERPAPI_API_KEY")
    if serp_key:
        try:
            with httpx.Client(timeout=SEARCH_TIMEOUT) as client:
                resp = client.get(
                    "https://serpapi.com/search",
                    params={
                        "api_key": serp_key,
                        "engine": "google",
                        "num": 5,
                        "q": query,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                snippets = [item.get("snippet", "") for item in data.get("organic_results", [])]
                combined = " ".join(snippets).strip()
                if combined:
                    return compact(combined)
        except Exception:
            pass

    return None


def llm_fallback(instruction: str, context: Optional[str] = None) -> str:
    """Ask the model directly when no search provider could answer."""
    prompt = "Respond with 200 characters or less.\n" + instruction.strip()
    if context:
        prompt += "\nContext:\n" + context.strip()

    response = llm.invoke(
        [
            SystemMessage(content="You are a concise travel assistant."),
            HumanMessage(content=prompt),
        ]
    )
    return compact(response.content)


def with_prefix(prefix: str, summary: str) -> str:
    """Prefix a summary with its label, keeping the total length bounded."""
    return compact(f"{prefix}: {summary}" if prefix else summary)