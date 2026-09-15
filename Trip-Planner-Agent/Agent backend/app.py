from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware

from agent import trip_agent


# FastAPI App
app = FastAPI(
    title="Trip Planner API",
    description="FastAPI backend for the Agno Trip Planner Agent",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Schema
class TripRequest(BaseModel):

    destination: str = Field(
        ...,
        description="Travel destination",
    )

    duration: str = Field(
        ...,
        description="Trip duration",
    )

    budget: str = Field(
        default="moderate",
        description="Travel budget",
    )

    interests: str = Field(
        default="local culture",
        description="Traveler interests",
    )


# Health Check
@app.get("/health")
async def health_check():

    return {
        "status": "healthy",
        "service": "trip-planner-agent",
    }


# Trip Planning
@app.post("/trip")
async def create_trip(request: TripRequest):

    try:

        query = f"""
Plan a {request.duration} trip to {request.destination}.

Focus on {request.interests}.

The travel budget preference is:
{request.budget}

Include:
- Essential information
- Budget breakdown appropriate for the selected budget
- Authentic local experiences
- Best massage experiences
"""

        response = trip_agent.run(
            query,
            stream=False,
        )

        return {
            "result": response.content,
            "destination": request.destination,
            "duration": request.duration,
            "budget": request.budget,
            "interests": request.interests,
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate trip plan: {str(e)}",
        )