"""
llm.py
======
Construction of the chat model used by every agent node.

The rest of the app never builds a model itself; it imports the shared `llm`
singleton from here. Keeping it in one file means "which provider are we using?"
has exactly one answer: Google Gemini.
"""

from __future__ import annotations

import os

from langchain_google_genai import ChatGoogleGenerativeAI

from config import IS_TEST_MODE


def _init_llm():
    """Return the chat model for this process.

    Priority:
      1. TEST_MODE -> a deterministic fake, so tests never hit the network.
      2. GOOGLE_API_KEY -> Gemini via the Google Generative AI API.
    """
    if IS_TEST_MODE:
        # Minimal stand-in that mimics the tiny slice of the interface we use
        # (`bind_tools` + `invoke`).
        class _Fake:
            def bind_tools(self, tools):
                return self

            def invoke(self, messages):
                class _Msg:
                    content = "Test itinerary"
                    tool_calls: list = []

                return _Msg()

        return _Fake()

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Please set GOOGLE_API_KEY in your .env")

    return ChatGoogleGenerativeAI(
        model=os.getenv("GOOGLE_MODEL", "gemini-2.5-flash"),
        google_api_key=api_key,
        temperature=0.7,
    )


# Shared model instance imported by the tools and the agent nodes.
llm = _init_llm()