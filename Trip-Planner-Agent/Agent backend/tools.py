import os
import httpx
from agno.tools import tool
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()

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

def _wiki_summary(dest: str) -> str:
    if not dest:
        return ""
    encoded_dest = quote(dest)

    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_dest}"
    HEADERS = { 'User-Agent': 'MyArizeApp/1.0 (ExampleContac@example.com)'}

    try:
        r = httpx.get(url, headers = HEADERS, timeout=5)
        r.raise_for_status()

        data = r.json().get("extract")
        return data if data else ""

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return ""
        return ""
    except httpx.RequestError as e:
        return ""
    except Exception as e:
        return ""

def _weather(dest):
    g = httpx.get(f"https://geocoding-api.open-meteo.com/v1/search?name={dest}")
    if g.status_code != 200 or not g.json().get("results"):
        return ""
    lat, lon = g.json()["results"][0]["latitude"], g.json()["results"][0]["longitude"]
    w = httpx.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}¤t_weather=true").json()
    cw = w.get("current_weather", {})
    return f"Weather now: {cw.get('temperature')}°C, wind {cw.get('windspeed')} km/h."


@tool
def essential_info(destination: str) -> str:
    """Get essential info (summary and weather) using APIs"""
    parts = []
    wiki = _wiki_summary(destination)
    if wiki: parts.append(wiki)
    weather = _weather(destination)
    if weather: parts.append(weather)
    return f"{destination} essentials:\n" + "\n".join(parts)

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