"""In the Parallelization framework, we run all sub-agents concurrently instead of sequentially. 
Each sub-agent works independently on its assigned task — for example, retrieving essential information, estimating budgets, 
or finding local experiences — while the main agent waits to gather their results. Once all sub-agents complete their work, 
the agent synthesizes their outputs into a unified response.

This approach offers a significant latency advantage, as parallel execution reduces overall response time without compromising 
the quality or completeness of the final answer."""

import os
import asyncio
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

from opentelemetry import trace
from openinference.semconv.trace import SpanAttributes

tracer = trace.get_tracer(__name__)

# Load environment variables
load_dotenv()


# ============================ API KEYS ============================

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


# ============================ OBSERVABILITY ============================

setup_observability()

# ============================ Parallelization Agent ============================

# --- Define Subagents ---
destination_agent = Agent(
    name="DestinationInfo",
    model=Gemini(id="gemini-2.5-flash"),
    tools=[essential_info],
    instructions=["Provide concise, reliable travel info for a destination using the essential_info tool."],
    debug_mode=True
)

budget_agent = Agent(
    name="Budget",
    model=Gemini(id="gemini-2.5-flash"),
    tools=[budget_basics],
    instructions=["Give clear travel budget summaries with hotel, meal, and transport cost ranges; give multiple options with prices and locations."],
    debug_mode=True
)

local_activity_agent = Agent(
    name="ActivitySuggester",
    model=Gemini(id="gemini-2.5-flash"),
    tools=[local_flavor],
    instructions=[
        "Group local activities by category: cultural, food, outdoors.",
        "Include both popular and hidden-gem recommendations."
    ],
    debug_mode=True
)

synthesizer = Agent(
    name="Synthesizer",
    model=Gemini(id="gemini-2.5-flash"),
    instructions=[
        "Combine partial responses into a clear, well-structured final answer."
    ],
    debug_mode=True
)

async def plan_trip(destination: str, duration: str, interests: str):

    with tracer.start_as_current_span("ParallelizationAgent") as span:

        span.set_attribute(
            SpanAttributes.OPENINFERENCE_SPAN_KIND,
            "agent"
        )
        span.set_attribute("destination", destination)
        span.set_attribute("duration", duration)
        span.set_attribute("interests", interests)

        print(f"\n🚀 Planning trip to {destination}...\n", flush=True)

        # ---------------------------------------------------------
        # Run all sub-agents concurrently
        # ---------------------------------------------------------

        dest_task = asyncio.create_task(
            destination_agent.arun(
                f"""
                Find essential travel information for {destination}.
                Use the essential_info tool.
                """
            )
        )

        budget_task = asyncio.create_task(
            budget_agent.arun(
                f"""
                Create a travel budget for {destination} for {duration}.
                Include hotel, food, and transportation costs.
                Give multiple options with prices and locations.
                Use the budget_basics tool.
                """
            )
        )

        local_task = asyncio.create_task(
            local_activity_agent.arun(
                f"""
                Find local activities in {destination}.
                The traveler's interests are: {interests}.
                Group activities into cultural, food, and outdoor categories.
                Include both popular attractions and hidden gems.
                Use the local_flavor tool.
                """
            )
        )

        print("⏳ Running destination, budget, and activity agents in parallel...", flush=True)

        # Wait for all three agents
        dest_info, budget_info, activities = await asyncio.gather(
            dest_task,
            budget_task,
            local_task
        )

        print("✅ All parallel agents completed.\n", flush=True)

        # ---------------------------------------------------------
        # Extract content
        # ---------------------------------------------------------

        dest_content = (
            dest_info.content
            if hasattr(dest_info, "content")
            else str(dest_info)
        )

        budget_content = (
            budget_info.content
            if hasattr(budget_info, "content")
            else str(budget_info)
        )

        activities_content = (
            activities.content
            if hasattr(activities, "content")
            else str(activities)
        )

        # ---------------------------------------------------------
        # Final synthesis
        # ---------------------------------------------------------

        final_prompt = f"""
        Create a cohesive, well-structured travel plan for {destination}.

        Trip duration: {duration}
        Interests: {interests}

        [Destination Information]
        {dest_content}

        [Budget Summary]
        {budget_content}

        [Local Activities]
        {activities_content}

        Combine all of the above into one practical travel plan.
        Keep it friendly, natural, and under 1000 words.
        """

        print("🧠 Synthesizing the results...", flush=True)

        final_plan = await synthesizer.arun(final_prompt)

        print("✅ Final plan generated.\n", flush=True)

        return final_plan


# ================================================================
# Run
# ================================================================

if __name__ == "__main__":

    destination = "Tokyo"
    duration = "5 days"
    interests = "food, culture"

    final = asyncio.run(
        plan_trip(
            destination,
            duration,
            interests
        )
    )

    print("=" * 80)
    print("FINAL TRAVEL PLAN")
    print("=" * 80)

    print(
        final.content
        if hasattr(final, "content")
        else final
    )