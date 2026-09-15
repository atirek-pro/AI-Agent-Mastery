# Agent Mastery — Learning Material & Reference Implementation

A hands-on course + working codebase for learning how to design, build, and evaluate AI agents — from first principles (what _is_ an agent?) all the way to a deployed, observable, multi-architecture reference application.

This repo is meant to be read **and** run. The `Learning Material/` folder teaches the concepts; the `Trip-Planner-Agent/` folder is a real agent built on those concepts, implementing three different agent architectures side by side so you can compare them directly instead of just reading about them.

---

## Who This Is For

| Audience                                 | What you'll get out of this repo                                                                                                                                                                                              |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **First-time agent builders**            | A structured, lecture-by-lecture path from "what is an agent" to a working, deployed system — no prior agent-framework experience assumed.                                                                                    |
| **AI/ML & Software Engineers**           | A reference implementation showing Routing, Orchestrator-Worker, and Parallelization architectures on the _same_ use case, plus production concerns: observability (OpenTelemetry/OpenInference/Arize), tool design, and RAG. |
| **AI Product Managers / Domain Experts** | Lecture 6 (Evaluation) and the "Overview" lecture explain how technical and non-technical roles split responsibility on an agent team, and how to reason about eval design without needing to read code.                      |

You don't need a technical background to get value from the `Learning Material/` lectures — but you do need to open the code in `Trip-Planner-Agent/` to see the concepts actually implemented.

---

## Repository Structure

```
atirek-pro-ai-agent-mastery/
├── Learning Material/              # The course: 7 lectures, concept-first
│   ├── Overview_Agents.md
│   ├── Lecture_1_Introduction_to_Agents.md
│   ├── Lecture_2_Agent_Engineering.md
│   ├── Lecture_3_Agent_Architecture.md
│   ├── Lecture_4_Tools_and_MCP.md
│   ├── Lecture_5_RAG_and_Agentic_RAG.md
│   └── Lecture_6_Agent_Evaluation.md
│
└── Trip-Planner-Agent/              # The reference implementation
    ├── requirements.txt
    ├── Agent backend/
    │   ├── agent.py                     # Single-agent baseline
    │   ├── orchestrator_worker_agent.py # Orchestrator-Worker architecture
    │   ├── parallelization_agent.py     # Parallelization architecture
    │   ├── tools.py                     # Tool definitions (data access/extraction)
    │   ├── observability.py             # OpenTelemetry + Arize instrumentation
    │   ├── app.py                       # FastAPI serving layer
    │   ├── local_guides.json            # RAG knowledge base
    │   └── rag/rag_tool.py              # FAISS-powered semantic retrieval tool
    └── Agent Frontend/
        └── index.html                   # Simple UI to call the agent API
```

---

## How to Get the Most Out of This Repo

The lectures and the code are designed to be worked through **together, in order** — each lecture unlocks a specific file in `Trip-Planner-Agent/`. Don't jump straight to the code; the lectures explain _why_ the code is structured the way it is, and the code is what makes the lecture concepts concrete.

### Recommended path

1. **`Overview_Agents.md`** — Read first. Defines what an agent is (Reasoning + Routing + Action), who builds agent teams, and how the 7 modules fit together.
2. **`Lecture_1_Introduction_to_Agents.md`** — Agent anatomy, common failure modes, and the eval categories that map to each part of an agent's execution. Ends with a hands-on task: run the Trip Advisor agent for the first time.
   - 👉 Pair with: `Trip-Planner-Agent/Agent backend/agent.py` (the simplest, single-agent version).
3. **`Lecture_2_Agent_Engineering.md`** — Product thinking before architecture, plus a deep dive into **observability** (traces, spans, OTel/OpenInference).
   - 👉 Pair with: `observability.py` — see exactly how traces/spans are instrumented in a real agent.
4. **`Lecture_3_Agent_Architecture.md`** — The four foundational architecture patterns: Routing, Orchestrator-Worker, Parallelization, Evaluator-Optimizer.
   - 👉 Pair with: `orchestrator_worker_agent.py` and `parallelization_agent.py` — the **same trip-planning task**, implemented two different ways, so you can directly compare control flow, latency trade-offs, and code structure.
5. **`Lecture_4_Tools_and_MCP.md`** — What tools are, tool categories, and how MCP standardizes tool access.
   - 👉 Pair with: `tools.py` — see Data Access, Extraction, and Analysis tools implemented as real Python functions the agent calls.
6. **`Lecture_5_RAG_and_Agentic_RAG.md`** — RAG fundamentals, its limitations, and how Agentic RAG solves them.
   - 👉 Pair with: `rag/rag_tool.py` and `local_guides.json` — a working FAISS-backed semantic retrieval tool the agent uses to ground its "local experiences" recommendations.
7. **`Lecture_6_Agent_Evaluation.md`** — Model eval vs. system eval, LLM-as-a-Judge vs. code-based evals, and how to design evals that are consistent, reproducible, and actionable.
   - 👉 This is where you'd wire up an eval harness against the traces produced by `observability.py`. (See the dedicated Evaluation repo linked below for a deeper, hands-on treatment of this lecture.)

### Then: run it yourself

Once you've read through the lectures in order:

1. Set up the backend: `cd "Trip-Planner-Agent/Agent backend" && pip install -r ../requirements.txt`
2. Configure your `.env` (API keys for your LLM provider, Tavily search, and Arize observability — see the top of each file for the expected environment variables).
3. Run the FastAPI server: `uvicorn app:app --reload`
4. Open `Trip-Planner-Agent/Agent Frontend/index.html` in your browser and plan a trip.
5. Try swapping which backend agent the frontend calls (`agent.py` vs. `orchestrator_worker_agent.py` vs. `parallelization_agent.py`) and compare the traces in your observability dashboard.

Each lecture ends with a **"Test Your Understanding"** section — use these as checkpoints before moving to the next lecture, especially if you're new to agents.

---

## How Different Roles Should Use This Repo

- **If you're building agents for the first time:** follow the path above linearly. Don't skip Lecture 1 and 2 — architecture and tools (Lectures 3–5) will feel arbitrary without the "what could go wrong" and "product thinking" foundations first.
- **If you're already building agents:** skim `Overview_Agents.md` and Lecture 1, then go straight to Lectures 3–5 and the corresponding architecture files. The three parallel implementations of the trip planner (`agent.py`, `orchestrator_worker_agent.py`, `parallelization_agent.py`) are the fastest way to see architectural trade-offs in real code rather than diagrams.
- **If you're an AI PM or domain expert (non-engineer):** focus on `Overview_Agents.md` (team composition), Lecture 1 (failure modes and why evals exist), and Lecture 6 (evaluation design principles — no code required to follow this one). You don't need to run the code to get value here, but skimming `tools.py` will help you understand what your engineers mean when they talk about "tools."

---

## Evaluation — Going Deeper

Lecture 6 in this repo covers the _concepts_ of agent evaluation (LLM-as-a-Judge, code-based evals, eval prompt design, designing good evals). For a dedicated, hands-on deep dive into **building a full evaluation pipeline** — including working eval harnesses, datasets, and rubrics — see the companion repo:

**[Agent Evaluation Deep Dive →](https://github.com/atirek-pro/Learn-Arize)**

---

## License

Add your license of choice here.
