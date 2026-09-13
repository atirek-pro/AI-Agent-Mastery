"""In the Orchestrator-Worker framework, we will structure our system using multiple specialized sub-agents 
(one for each of our 3 tools).
Each sub-agent focuses on a specific capability, such as getting essential information, estimating budgets, 
or suggesting local experiences.
A centralized orchestrator agent coordinates these sub-agents by delegating tasks to the appropriate one and 
then synthesizing their outputs into a cohesive final response. This approach mirrors how complex workflows can be
broken down into smaller, focused tasks that work together seamlessly."""

import os
from dotenv import load_dotenv
from observability import setup_observability
from tools import (
    essential_info,
    budget_basics,
    local_flavor,
)

from agno.agent import Agent
from agno.team import Team
from agno.models.google import Gemini

# Load environment variables
load_dotenv()


# ============================ API KEYS ============================

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


# ============================ OBSERVABILITY ============================

setup_observability()

# ============================ Orchestrator Agent ============================

# --- Define Subagents ---
destination_agent = Agent(
    name="DestinationInfo",
    model=Gemini(id="gemini-2.5-flash"),
    description="Get basic travel info (weather, best time, attractions, etiquette).",
    instructions=["Provide concise, reliable travel info for a destination using the essential_info tool."],
    tools=[essential_info],
)

budget_agent = Agent(
    name="Budget",
    model=Gemini(id="gemini-2.5-flash"),
    description="Summarize travel cost.",
    instructions=["Give clear travel budget summaries with hotel, meal, and transport cost ranges; give multiple options with prices and locations."],
    tools = [budget_basics],
    markdown=True,
)

local_activity_agent = Agent(
    name="ActivitySuggester",
    model=Gemini(id="gemini-2.5-flash"),
    description="Suggest authentic local experiences.",
    instructions=[
        "Group local activities by category: cultural, food, outdoors.",
        "Include both popular and hidden-gem recommendations."
    ],
    tools=[local_flavor],
    markdown=True,
)

travel_team = Team(
    name="Orchestrator-TripPlanner",
    members=[destination_agent, budget_agent, local_activity_agent],
    model=Gemini(id="gemini-2.5-flash"),
    instructions=[
        "You are a friendly and knowledgeable travel planner. "
        "Combine coordinate agents to create a trip plan including essentials, budget, and local flavor. "
        "Keep the tone natural, clear, and under 1000 words."
    ],
    show_members_responses=True,
    markdown=True,
)

# --- Example usage ---
destination = "Tokyo"
duration = "5 days"
interests = "food, culture"

query = f"""
Plan a {duration} trip to {destination}.
Focus on {interests}.
Include essential info, budget breakdown, and local experiences.
"""
travel_team.print_response(
  query,
  stream=True
)