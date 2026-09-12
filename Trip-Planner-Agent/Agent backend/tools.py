"""
tools.py
========
The LangChain tools the agents are allowed to call.

Each tool follows the same shape:
  1. try a live web search for the most current answer;
  2. if search is unavailable, fall back to the LLM.

That keeps the demo useful with or without search API keys.
"""

from __future__ import annotations

from typing import List, Optional

from langchain_core.tools import tool

from search import llm_fallback, search_api, with_prefix


@tool
def essential_info(destination: str) -> str:
    """Return essential destination info like weather, sights, and etiquette."""
    query = (
        f"{destination} travel essentials weather best time top attractions "
        "etiquette language currency safety"
    )
    summary = search_api(query)
    if summary:
        return with_prefix(f"{destination} essentials", summary)

    instruction = (
        f"Summarize the climate, best visit time, standout sights, customs, "
        f"language, currency, and safety tips for {destination}."
    )
    return llm_fallback(instruction)


@tool
def budget_basics(destination: str, duration: str) -> str:
    """Return high-level budget categories for a given destination and duration."""
    query = f"{destination} travel budget average daily costs {duration}"
    summary = search_api(query)
    if summary:
        return with_prefix(f"{destination} budget {duration}", summary)

    instruction = (
        f"Outline lodging, meals, transport, activities, and extra costs for a "
        f"{duration} trip to {destination}."
    )
    return llm_fallback(instruction)


@tool
def local_flavor(destination: str, interests: Optional[str] = None) -> str:
    """Suggest authentic local experiences matching optional interests."""
    focus = interests or "local culture"
    query = f"{destination} authentic local experiences {focus}"
    summary = search_api(query)
    if summary:
        return with_prefix(f"{destination} {focus}", summary)

    instruction = f"Recommend authentic local experiences in {destination} that highlight {focus}."
    return llm_fallback(instruction)


@tool
def day_plan(destination: str, day: int) -> str:
    """Return a simple day plan outline for a specific day number."""
    query = f"{destination} day {day} itinerary highlights"
    summary = search_api(query)
    if summary:
        return with_prefix(f"Day {day} in {destination}", summary)

    instruction = (
        f"Outline key activities for day {day} in {destination}, covering "
        "morning, afternoon, and evening."
    )
    return llm_fallback(instruction)


@tool
def weather_brief(destination: str) -> str:
    """Return a brief weather summary for planning purposes."""
    query = f"{destination} weather forecast travel season temperatures rainfall"
    summary = search_api(query)
    if summary:
        return with_prefix(f"{destination} weather", summary)

    instruction = (
        f"Give a weather brief for {destination} noting season, temperatures, "
        "rainfall, humidity, and packing guidance."
    )
    return llm_fallback(instruction)


@tool
def visa_brief(destination: str) -> str:
    """Return a brief visa guidance placeholder for tutorial purposes."""
    query = f"{destination} tourist visa requirements entry rules"
    summary = search_api(query)
    if summary:
        return with_prefix(f"{destination} visa", summary)

    instruction = (
        f"Provide a visa guidance summary for visiting {destination}, including "
        "advice to confirm with the relevant embassy."
    )
    return llm_fallback(instruction)


@tool
def attraction_prices(destination: str, attractions: Optional[List[str]] = None) -> str:
    """Return rough placeholder prices for attractions."""
    items = attractions or ["popular attractions"]
    focus = ", ".join(items)
    query = f"{destination} attraction ticket prices {focus}"
    summary = search_api(query)
    if summary:
        return with_prefix(f"{destination} attraction prices", summary)

    instruction = (
        f"Share typical ticket prices and savings tips for attractions such as "
        f"{focus} in {destination}."
    )
    return llm_fallback(instruction)


@tool
def local_customs(destination: str) -> str:
    """Return simple etiquette reminders for the destination."""
    query = f"{destination} cultural etiquette travel customs"
    summary = search_api(query)
    if summary:
        return with_prefix(f"{destination} customs", summary)

    instruction = (
        f"Summarize key etiquette and cultural customs travelers should know "
        f"before visiting {destination}."
    )
    return llm_fallback(instruction)


@tool
def hidden_gems(destination: str) -> str:
    """Return a few off-the-beaten-path ideas."""
    query = f"{destination} hidden gems local secrets lesser known spots"
    summary = search_api(query)
    if summary:
        return with_prefix(f"{destination} hidden gems", summary)

    instruction = f"List lesser-known attractions or experiences that feel like hidden gems in {destination}."
    return llm_fallback(instruction)


@tool
def travel_time(from_location: str, to_location: str, mode: str = "public") -> str:
    """Return an approximate travel time placeholder."""
    query = f"travel time {from_location} to {to_location} by {mode}"
    summary = search_api(query)
    if summary:
        return with_prefix(f"{from_location}→{to_location} {mode}", summary)

    instruction = (
        f"Estimate the travel time from {from_location} to {to_location} by "
        f"{mode}, providing a realistic range."
    )
    context = f"From: {from_location}\nTo: {to_location}\nMode: {mode}"
    return llm_fallback(instruction, context=context)


@tool
def packing_list(destination: str, duration: str, activities: Optional[List[str]] = None) -> str:
    """Return a generic packing list summary."""
    acts = ", ".join(activities or ["sightseeing"])
    query = f"what to pack for {destination} {duration} {acts}"
    summary = search_api(query)
    if summary:
        return with_prefix(f"{destination} packing", summary)

    instruction = f"Suggest packing essentials for a {duration} trip to {destination} focused on {acts}."
    context = f"Destination: {destination}\nDuration: {duration}\nActivities: {acts}"
    return llm_fallback(instruction, context=context)