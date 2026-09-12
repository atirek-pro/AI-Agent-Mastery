"""
schemas.py
==========
Pydantic models describing the HTTP contract.

They live apart from `app.py` so the API surface can be imported (e.g. by tests
or a client generator) without pulling in FastAPI or the agent graph.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class TripRequest(BaseModel):
    """What the client sends to POST /plan-trip."""

    destination: str
    duration: str
    budget: Optional[str] = None
    interests: Optional[str] = None
    travel_style: Optional[str] = None


class TripResponse(BaseModel):
    """What the client gets back: the itinerary plus the tools that were used."""

    result: str
    tool_calls: List[Dict[str, Any]] = []