"""Simple coding Q&A agent - test ground for agent monitoring platform.

Usage:
    python test_monitoring.py              # interactive REPL
    python test_monitoring.py "your question"  # single question

Requires: REGOLO_API_KEY in .env (optionally REGOLO_MODEL)
Monitoring: DATAPIZZA_MONITORING_API_KEY, DATAPIZZA_PROJECT_ID in .env
"""
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import contextlib
import io

from datapizza.clients.openai_like import OpenAILikeClient
from datapizza.agents import Agent
from datapizza.tools import tool

REGOLO_API_KEY = os.getenv("REGOLO_API_KEY")
REGOLO_MODEL = os.getenv("REGOLO_MODEL", "gpt-oss-120b")
REGOLO_BASE_URL = "https://api.regolo.ai/v1"

# Datapizza monitoring (optional)
DATAPIZZA_OTLP_ENDPOINT = os.getenv(
    "DATAPIZZA_OTLP_ENDPOINT",
    "https://datapizza-monitoring.datapizza.tech/gateway/v1/traces",
)
DATAPIZZA_API_KEY = os.getenv("DATAPIZZA_MONITORING_API_KEY")
DATAPIZZA_PROJECT_ID = os.getenv("DATAPIZZA_MONITORING_PROJECT_ID")

# Setup monitoring tracer (optional)
_tracer = None
if DATAPIZZA_API_KEY and DATAPIZZA_PROJECT_ID:
    try:
        from datapizza.tracing import DatapizzaMonitoringInstrumentor

        instrumentor = DatapizzaMonitoringInstrumentor(
            api_key=DATAPIZZA_API_KEY,
            project_id=DATAPIZZA_PROJECT_ID,
            endpoint=DATAPIZZA_OTLP_ENDPOINT,
        )
        instrumentor.instrument()
        _tracer = instrumentor.get_tracer(__name__)
    except ImportError:
        pass

SYSTEM_PROMPT = """You are a helpful coding assistant. Answer programming questions clearly and concisely.
When relevant, provide code snippets with proper syntax highlighting hints.
Use the execute_python tool to run code when the user asks to execute, run, or test Python code.
Focus on correctness, best practices, and readability."""


@tool
def execute_python(code: str) -> str:
    """Execute Python code and return the output. Use for running snippets, calculations, or demos.
    The code runs in a restricted environment with basic builtins (print, len, range, etc.).
    Returns stdout/stderr output or the error message if execution fails."""
    output_buffer = io.StringIO()
    safe_builtins = {
        "print": print,
        "len": len,
        "range": range,
        "sum": sum,
        "min": min,
        "max": max,
        "abs": abs,
        "round": round,
        "sorted": sorted,
        "list": list,
        "dict": dict,
        "set": set,
        "tuple": tuple,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "enumerate": enumerate,
        "zip": zip,
        "map": map,
        "filter": filter,
    }
    state = {"__builtins__": safe_builtins}
    with contextlib.redirect_stdout(output_buffer), contextlib.redirect_stderr(output_buffer):
        try:
            exec(code, state)
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"
    return output_buffer.getvalue() or "(no output)"


def create_coding_agent() -> Agent:
    """Create the coding agent with the configured LLM client."""
    if not REGOLO_API_KEY:
        raise ValueError("REGOLO_API_KEY not set in .env")

    client = OpenAILikeClient(
        api_key=REGOLO_API_KEY,
        model=REGOLO_MODEL,
        base_url=REGOLO_BASE_URL,
    )

    return Agent(
        name="coding_assistant",
        client=client,
        system_prompt=SYSTEM_PROMPT,
        tools=[execute_python],
    )


def answer_question(agent: Agent, question: str) -> str:
    """Run the agent on a question and return the response text."""
    def _run() -> str:
        response = agent.run(question)
        return response.text if response else ""

    if _tracer is not None:
        with _tracer.start_as_current_span("coding_agent.answer") as span:
            span.set_attribute("question", question[:500])
            result = _run()
            span.set_attribute("response_length", len(result))
            return result
    return _run()


def run_interactive(agent: Agent) -> None:
    """REPL loop for interactive coding questions."""
    print("Coding assistant ready. Type your question (or 'quit' to exit).\n")
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break
        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Bye!")
            break

        try:
            answer = answer_question(agent, question)
            print(f"\nAssistant: {answer}\n")
        except Exception as e:
            print(f"\nError: {e}\n")


def main() -> None:
    agent = create_coding_agent()

    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        answer = answer_question(agent, question)
        print(answer)
    else:
        run_interactive(agent)


if __name__ == "__main__":
    main()
