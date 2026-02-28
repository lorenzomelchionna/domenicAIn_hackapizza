"""Multi-agent setup for monitoring dashboard testing.

Coordinator agent receives user questions and delegates coding questions
to the coding expert. Both agents have tools, producing a trace tree for
the monitoring dashboard.

Usage:
    python test_monitoring_multiagent.py              # interactive
    python test_monitoring_multiagent.py "your question"

Flow: User -> Coordinator -> [ask_coding_expert] -> Coding Agent -> [execute_python]
"""
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from datapizza.agents import Agent
from datapizza.clients.openai_like import OpenAILikeClient
from datapizza.tools import tool

# Import coding agent and shared config from test_monitoring
from test_monitoring import (
    REGOLO_API_KEY,
    REGOLO_MODEL,
    REGOLO_BASE_URL,
    _tracer,
    create_coding_agent,
)

COORDINATOR_PROMPT = """You are a helpful coordinator. You route questions to the right expert.
- For coding, Python, or programming questions: use ask_coding_expert.
- For general chat or non-coding questions: use quick_lookup, then respond briefly.
Always be concise."""


@tool
def quick_lookup(topic: str) -> str:
    """Quick lookup for general topics. Returns a brief fact. Use for non-coding questions."""
    facts = {
        "hello": "Hello! How can I help you today?",
        "weather": "I don't have live weather data. Ask about coding instead!",
        "time": "I focus on coding help. For time, check your system clock.",
    }
    return facts.get(topic.lower(), f"No specific info on '{topic}'. Try asking the coding expert for technical questions.")


def make_ask_coding_expert_tool(coding_agent: Agent):
    """Create a tool that delegates to the coding agent."""

    @tool
    def ask_coding_expert(question: str) -> str:
        """Delegate a coding or programming question to the coding expert. Use for Python, code, or technical questions."""
        response = coding_agent.run(question)
        return response.text if response else ""

    return ask_coding_expert


def create_coordinator_agent(coding_agent: Agent) -> Agent:
    """Create the coordinator agent with delegation to coding expert."""
    client = OpenAILikeClient(
        api_key=REGOLO_API_KEY,
        model=REGOLO_MODEL,
        base_url=REGOLO_BASE_URL,
    )
    ask_expert = make_ask_coding_expert_tool(coding_agent)
    return Agent(
        name="coordinator",
        client=client,
        system_prompt=COORDINATOR_PROMPT,
        tools=[ask_expert, quick_lookup],
    )


def run_coordinator(coordinator: Agent, question: str) -> str:
    """Run coordinator on a question (with optional tracing)."""
    def _run() -> str:
        response = coordinator.run(question)
        return response.text if response else ""

    if _tracer is not None:
        with _tracer.start_as_current_span("coordinator.answer") as span:
            span.set_attribute("question", question[:500])
            result = _run()
            span.set_attribute("response_length", len(result))
            return result
    return _run()


def main() -> None:
    coding_agent = create_coding_agent()
    coordinator = create_coordinator_agent(coding_agent)

    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        print(run_coordinator(coordinator, question))
    else:
        print("Multi-agent coordinator ready. Ask anything (coding questions go to the expert).\n")
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
                answer = run_coordinator(coordinator, question)
                print(f"\nAssistant: {answer}\n")
            except Exception as e:
                print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
