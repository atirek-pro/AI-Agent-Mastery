import os
from dotenv import load_dotenv

from observability import setup_observability

from tools import (
    essential_info,
    budget_basics,
)

from rag.rag_tool import local_flavor_rag_powered

from agno.agent import Agent
from agno.models.google import Gemini


# Load environment variables
load_dotenv()


# API KEYS
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


# OBSERVABILITY
setup_observability()


# Main Agent
trip_agent = Agent(
    name="TripPlanner",
    role="AI Travel Assistant",

    model=Gemini(
        id="gemini-2.5-flash"
    ),

    instructions=(
        "You are a friendly and knowledgeable travel planner. "
        "Combine multiple tools to create a trip plan including "
        "essentials, budget, and local flavor. "
        "Keep the tone natural, clear, and under 1000 words."
    ),

    markdown=True,

    tools=[
        essential_info,
        budget_basics,
        local_flavor_rag_powered,
    ],
)


# Example usage
# destination = "Thailand"
# duration = "10 days"
# interests = "food, culture, Night Life"

# query = f"""
# Plan a {duration} trip to {destination}.

# Focus on {interests}.

# Include:
# - Essential information
# - Budget breakdown
# - Authentic local experiences
# - Best massage experiences
# """

# trip_agent.print_response(
#     query,
#     stream=True
# )