"""
rag/generation.py
=================
Stage 3 of RAG: generation.

Takes the documents returned by the retriever and produces the local-guide
answer: builds the numbered context block, formats the prompt, lets the model
call its tools, and appends the citations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import ToolNode

from config import ENABLE_RAG
from llm import llm
from observability import using_prompt_template

# Prompt template for the local-guide stage. Kept at module level so it is easy
# to find and to version (it is reported to the tracer as "v1").
LOCAL_GUIDE_PROMPT = (
    "You are a local guide.\n"
    "Use the retrieved travel notes to suggest authentic experiences in {destination} "
    "for interests: {interests}.\n"
    "Context:\n{context}\n"
    "Cite the numbered items when you rely on them."
)


def build_local_context(
    retrieved: List[Dict[str, Any]],
    *,
    destination: str,
) -> Tuple[str, List[str]]:
    """Turn retriever hits into (numbered context block, citation lines).

    The context block is what the model reads; the citation lines are appended
    to the final answer so a reader can trace claims back to a source.
    """
    context_lines: List[str] = []
    citation_lines: List[str] = []

    for idx, item in enumerate(retrieved, start=1):
        meta = item.get("metadata", {})
        label = meta.get("city") or destination
        context_lines.append(f"[{idx}] {label}: {item.get('content')}")
        if meta.get("source"):
            citation_lines.append(f"[{idx}] {meta['source']}")

    if context_lines:
        context_text = "\n".join(context_lines)
    elif ENABLE_RAG:
        context_text = "No curated context available."
    else:
        context_text = "Context unavailable because ENABLE_RAG is disabled."

    return context_text, citation_lines


def generate_local_recommendations(
    *,
    destination: str,
    interests: str,
    context_text: str,
    citation_lines: List[str],
    tools: List[Any],
) -> Tuple[str, List[Dict[str, Any]]]:
    """Generate the local-guide answer, executing any tool calls the model makes.

    Returns the answer text (with sources appended) and a list describing the
    tools that were called, for the API response and the trace.
    """
    variables = {
        "destination": destination,
        "interests": interests,
        "context": context_text,
    }

    # `using_prompt_template` annotates the span with the template + variables.
    with using_prompt_template(template=LOCAL_GUIDE_PROMPT, variables=variables, version="v1"):
        agent = llm.bind_tools(tools)
        response = agent.invoke([
            HumanMessage(content=LOCAL_GUIDE_PROMPT.format(**variables))
        ])

    answer = response.content
    tool_calls: List[Dict[str, Any]] = []

    if getattr(response, "tool_calls", None):
        for call in response.tool_calls:
            tool_calls.append(
                {"agent": "local", "tool": call["name"], "args": call.get("args", {})}
            )

        # Run the requested tools and use the last message as the answer.
        tool_node = ToolNode(tools)
        tool_result = tool_node.invoke({"messages": [response]})
        messages = tool_result["messages"]
        answer = messages[-1].content if messages else answer

    if citation_lines:
        answer = f"{answer}\n\nSources:\n" + "\n".join(citation_lines)

    return answer, tool_calls