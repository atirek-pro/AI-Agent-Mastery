"""
agent.py
========
The LangChain + LangGraph layer.

This file knows about exactly two things: the shared state (`TripState`) and the
graph that moves a trip request through four nodes:

    START ─┬─> research ──┐
           ├─> budget   ──┼─> itinerary ──> END
           └─> local    ──┘

The first three nodes run in parallel; the itinerary node waits for all of them.
Anything that is *not* graph plumbing (LLM setup, tools, RAG, tracing, HTTP)
lives in its own module - see config.py, llm.py, tools.py, rag/, observability.py.
"""

from __future__ import annotations

import operator
from typing import Any, Dict, List, Optional

from typing_extensions import Annotated, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from config import ENABLE_MCP
from llm import llm
from mcp_weather import mcp_weather
from observability import using_prompt_template
from rag.generation import build_local_context, generate_local_recommendations, LOCAL_GUIDE_PROMPT
from rag.retriever import LOCAL_GUIDE_RETRIEVER
from tools import (
    attraction_prices,
    budget_basics,
    essential_info,
    hidden_gems,
    local_customs,
    local_flavor,
    visa_brief,
    weather_brief,
)


# ---------------------------------------------------------------------------
# Shared graph state
# ---------------------------------------------------------------------------
class TripState(TypedDict):
    """State passed between nodes.

    `messages` and `tool_calls` use `operator.add` so parallel branches merge
    their contributions instead of overwriting each other.
    """

    messages: Annotated[List[BaseMessage], operator.add]
    trip_request: Dict[str, Any]
    research: Optional[str]
    budget: Optional[str]
    local: Optional[str]
    local_context: Optional[str]
    final: Optional[str]
    tool_calls: Annotated[List[Dict[str, Any]], operator.add]


# ---------------------------------------------------------------------------
# Node: research
# ---------------------------------------------------------------------------
def research_agent(state: TripState) -> TripState:
    """Gather essential destination information (weather, visas, sights)."""
    req = state["trip_request"]
    destination = req["destination"]

    if ENABLE_MCP:
        prompt_t = (
            "You are a research assistant.\n"
            "First, call the mcp_weather tool to get weather for {destination}.\n"
            "Then use other tools as needed for additional information."
        )
    else:
        prompt_t = (
            "You are a research assistant.\n"
            "Gather essential information about {destination}.\n"
            "Use at most one tool if needed."
        )

    variables = {"destination": destination}
    tools = [essential_info, weather_brief, visa_brief]
    if ENABLE_MCP:
        tools.append(mcp_weather)

    with using_prompt_template(template=prompt_t, variables=variables, version="v1"):
        agent = llm.bind_tools(tools)
        response = agent.invoke([
            HumanMessage(content=prompt_t.format(**variables))
        ])

    output = response.content
    calls: List[Dict[str, Any]] = []

    # If the model asked for tools, execute them and take the tool output.
    if getattr(response, "tool_calls", None):
        for call in response.tool_calls:
            calls.append({"agent": "research", "tool": call["name"], "args": call.get("args", {})})

        tool_result = ToolNode(tools).invoke({"messages": [response]})
        messages = tool_result["messages"]
        output = messages[-1].content if messages else output

    return {"messages": [HumanMessage(content=output)], "research": output, "tool_calls": calls}


# ---------------------------------------------------------------------------
# Node: budget
# ---------------------------------------------------------------------------
def budget_agent(state: TripState) -> TripState:
    """Estimate costs, then ask the model for a structured breakdown."""
    req = state["trip_request"]
    destination, duration = req["destination"], req["duration"]
    budget = req.get("budget", "moderate")

    prompt_t = (
        "You are a budget analyst.\n"
        "Analyze costs for {destination} over {duration} with budget: {budget}.\n"
        "Use tools to get pricing information, then provide a detailed breakdown."
    )
    variables = {"destination": destination, "duration": duration, "budget": budget}

    messages = [HumanMessage(content=prompt_t.format(**variables))]
    tools = [budget_basics, attraction_prices]

    calls: List[Dict[str, Any]] = []

    with using_prompt_template(template=prompt_t, variables=variables, version="v1"):
        agent = llm.bind_tools(tools)
        response = agent.invoke(messages)

    if getattr(response, "tool_calls", None):
        for call in response.tool_calls:
            calls.append({"agent": "budget", "tool": call["name"], "args": call.get("args", {})})

        tool_result = ToolNode(tools).invoke({"messages": [response]})

        # Feed the tool results back in and ask for a final synthesis.
        messages.append(response)
        messages.extend(tool_result["messages"])
        messages.append(
            HumanMessage(
                content=(
                    f"Create a detailed budget breakdown for {duration} in "
                    f"{destination} with a {budget} budget."
                )
            )
        )
        output = llm.invoke(messages).content
    else:
        output = response.content

    return {"messages": [HumanMessage(content=output)], "budget": output, "tool_calls": calls}


# ---------------------------------------------------------------------------
# Node: local (RAG)
# ---------------------------------------------------------------------------
def local_agent(state: TripState) -> TripState:
    """Retrieve curated notes, then generate local recommendations from them.

    The RAG stages themselves live in `rag/`; this node just wires them to the
    graph state.
    """
    req = state["trip_request"]
    destination = req["destination"]
    interests = req.get("interests", "local culture")

    # Stage 2: retrieval.
    retrieved = LOCAL_GUIDE_RETRIEVER.retrieve(destination, interests)

    # Stage 3: generation (context block + prompt + tools + citations).
    context_text, citation_lines = build_local_context(retrieved, destination=destination)
    tools = [local_flavor, local_customs, hidden_gems]
    output, calls = generate_local_recommendations(
        destination=destination,
        interests=interests,
        context_text=context_text,
        citation_lines=citation_lines,
        tools=tools,
    )

    # Surface the retrieval itself in the trace so observability dashboards can
    # show which documents were used and how they scored.
    if retrieved:
        calls.insert(
            0,
            {
                "agent": "local",
                "tool": "local_guides_retriever",
                "args": {
                    "destination": destination,
                    "interests": interests,
                    "results": [
                        {
                            "city": item.get("metadata", {}).get("city"),
                            "source": item.get("metadata", {}).get("source"),
                            "score": round(float(item.get("score", 0.0)), 4),
                        }
                        for item in retrieved
                    ],
                },
            },
        )

    return {
        "messages": [HumanMessage(content=output)],
        "local": output,
        "local_context": context_text,
        "tool_calls": calls,
    }


# ---------------------------------------------------------------------------
# Node: itinerary (fan-in)
# ---------------------------------------------------------------------------
def itinerary_agent(state: TripState) -> TripState:
    """Combine the three research streams into the final itinerary."""
    req = state["trip_request"]
    destination = req["destination"]
    duration = req["duration"]
    travel_style = req.get("travel_style", "standard")

    prompt_t = (
        "Create a {duration} itinerary for {destination} ({travel_style}).\n\n"
        "Inputs:\nResearch: {research}\nBudget: {budget}\nLocal: {local}\n"
    )
    variables = {
        "duration": duration,
        "destination": destination,
        "travel_style": travel_style,
        # Truncate upstream outputs so the final prompt stays a sane size.
        "research": (state.get("research") or "")[:400],
        "budget": (state.get("budget") or "")[:400],
        "local": (state.get("local") or "")[:400],
    }

    with using_prompt_template(template=prompt_t, variables=variables, version="v1"):
        response = llm.invoke([HumanMessage(content=prompt_t.format(**variables))])

    return {"messages": [HumanMessage(content=response.content)], "final": response.content}


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------
def build_graph():
    """Build and compile the trip-planner graph.

    Compiled without a checkpointer: the demo is stateless, so there is no state
    persistence to worry about.
    """
    graph = StateGraph(TripState)

    graph.add_node("research_node", research_agent)
    graph.add_node("budget_node", budget_agent)
    graph.add_node("local_node", local_agent)
    graph.add_node("itinerary_node", itinerary_agent)

    # Fan out: research, budget and local all start from START in parallel.
    graph.add_edge(START, "research_node")
    graph.add_edge(START, "budget_node")
    graph.add_edge(START, "local_node")

    # Fan in: the itinerary node runs only once all three have finished.
    graph.add_edge("research_node", "itinerary_node")
    graph.add_edge("budget_node", "itinerary_node")
    graph.add_edge("local_node", "itinerary_node")

    graph.add_edge("itinerary_node", END)

    return graph.compile()