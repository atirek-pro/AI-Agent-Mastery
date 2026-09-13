import os
import httpx
from agno.tools import tool

# --- Helper functions for tools ---

def _search_api(query: str) -> str | None:
    """Try Tavily search first, fall back to None."""
    tavily_key = os.getenv("TAVILY_API_KEY")
    if not tavily_key:
        return None
    try:
        resp = httpx.post(
            "https://api.tavily.com/search",
            json={
                "api_key": tavily_key,
                "query": query,
                "max_results": 3,
                "search_depth": "basic",
                "include_answer": True,
            },
            timeout=8,
        )
        data = resp.json()
        answer = data.get("answer") or ""
        snippets = [r.get("content", "") for r in data.get("results", [])]
        combined = " ".join([answer] + snippets).strip()
        return combined[:400] if combined else None
    except Exception:
        return None


def _compact(text: str, limit: int = 200) -> str:
    """Compact text for cleaner outputs."""
    cleaned = " ".join(text.split())
    return cleaned if len(cleaned) <= limit else cleaned[:limit].rsplit(" ", 1)[0]

@tool
def essential_info(destination: str) -> str:
    """Get basic travel info (weather, best time, attractions, etiquette)."""
    q = f"{destination} travel essentials weather best time top attractions etiquette"
    s = _search_api(q)
    if s:
        return f"{destination} essentials: {_compact(s)}"

    return f"{destination} is a popular travel destination. Expect local culture, cuisine, and landmarks worth exploring."

@tool
def budget_basics(destination: str, duration: str) -> str:
    """Summarize travel cost categories."""
    q = f"{destination} travel budget average daily costs {duration}"
    s = _search_api(q)
    if s:
        return f"{destination} budget ({duration}): {_compact(s)}"
    return f"Budget for {duration} in {destination} depends on lodging, meals, transport, and attractions."

@tool
def local_flavor(destination: str, interests: str = "local culture") -> str:
    """Suggest authentic local experiences."""
    q = f"{destination} authentic local experiences {interests}"
    s = _search_api(q)
    if s:
        return f"{destination} {interests}: {_compact(s)}"
    return f"Explore {destination}'s unique {interests} through markets, neighborhoods, and local eateries."