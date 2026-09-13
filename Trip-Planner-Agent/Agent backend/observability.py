import os

from arize.otel import register
from opentelemetry import trace
from openinference.instrumentation.agno import AgnoInstrumentor
from openinference.instrumentation.google_genai import GoogleGenAIInstrumentor

PROJECT_NAME = "Trip Planner Agent"


def setup_observability():
    tracer_provider = register(
        space_id=os.getenv("ARIZE_SPACE_ID"),
        api_key=os.getenv("ARIZE_API_KEY"),
        project_name=PROJECT_NAME,
        set_global_tracer_provider=True,
    )

    GoogleGenAIInstrumentor().instrument(
        tracer_provider=tracer_provider
    )

    AgnoInstrumentor().instrument(
        tracer_provider=tracer_provider
    )

    tracer = trace.get_tracer(__name__)