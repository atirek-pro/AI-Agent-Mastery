"""
app.py
======
The HTTP layer: FastAPI app, routes, and the dev entrypoint.

Run it with:

    uvicorn app:app --reload --port 8000      # from the "Agent backend" folder
    python app.py                             # or directly

All the interesting logic lives elsewhere; this file only translates HTTP
requests into graph invocations and back.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from agent import build_graph
from observability import init_tracing
from schemas import TripRequest, TripResponse

# ---------------------------------------------------------------------------
# App + middleware
# ---------------------------------------------------------------------------
app = FastAPI(title="AI Trip Planner")

# Wide-open CORS so the local frontend can call the API from any port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/")
def serve_frontend():
    """Serve the static frontend if it exists next to the backend folder."""
    here = os.path.dirname(__file__)
    path = os.path.join(here, "..", "frontend", "index.html")
    if os.path.exists(path):
        return FileResponse(path)
    return {"message": "frontend/index.html not found"}


@app.get("/health")
def health():
    """Liveness probe."""
    return {"status": "healthy", "service": "ai-trip-planner"}


@app.post("/plan-trip", response_model=TripResponse)
def plan_trip(req: TripRequest):
    """Run the full trip-planner graph for one request.

    A fresh graph is built per request; without a checkpointer it holds no state
    between calls, so this stays cheap and side-effect free.
    """
    graph = build_graph()

    # Only the inputs are seeded here - `research`, `budget`, `local` and
    # `final` are filled in by the nodes as the graph executes.
    state = {
        "messages": [],
        "trip_request": req.model_dump(),
        "tool_calls": [],
    }

    out = graph.invoke(state)
    return TripResponse(result=out.get("final", ""), tool_calls=out.get("tool_calls", []))


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
# Configure Arize/OpenInference tracing once, at import time, instead of on
# every request. No-ops when the credentials are missing.
init_tracing()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)