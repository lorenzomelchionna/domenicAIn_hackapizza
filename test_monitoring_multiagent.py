"""Multi-agent orchestrator-subagents setup for monitoring dashboard verification.

Uses datapizza's can_call() pattern (orchestrator delegates to sub-agents).
Run this and check the Datapizza Monitoring dashboard to verify whether
sub-agent invocations appear as child spans when the orchestrator delegates.

Usage:
    python test_monitoring_multiagent.py              # interactive
    python test_monitoring_multiagent.py "your question"

Flow: User -> Orchestrator -> [can_call] -> Coding Assistant / General Assistant
      Orchestrator has no tools; it delegates to sub-agents via can_call().
      Sub-agents have tools: coding_assistant has execute_python, general_assistant has quick_lookup.

Dashboard check: Look for child spans under "orchestrator.answer" when the orchestrator
delegates. If datapizza auto-instruments can_call, you'll see coding_assistant/general_assistant.
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

# Import from test_monitoring
from test_monitoring import (
    REGOLO_API_KEY,
    REGOLO_MODEL,
    REGOLO_BASE_URL,
    _tracer,
    create_coding_agent,
)

ORCHESTRATOR_PROMPT = """You are an orchestrator that routes questions to the right expert.
- For coding, Python, or programming questions: delegate to coding_assistant.
- For general chat, greetings, or non-coding questions: delegate to general_assistant.
Always delegate; do not answer directly. Be concise in your final summary to the user."""

GENERAL_ASSISTANT_PROMPT = """You are a general assistant for non-technical questions.
Use the quick_lookup tool for simple topics. Keep responses brief."""


@tool
def quick_lookup(topic: str) -> str:
    """Quick lookup for general topics. Returns a brief fact. Use for non-coding questions."""
    facts = {
        "hello": "Hello! How can I help you today?",
        "weather": "I don't have live weather data. Ask about coding instead!",
        "time": "I focus on coding help. For time, check your system clock.",
    }
    return facts.get(topic.lower(), f"No specific info on '{topic}'. Try the coding assistant for technical questions.")


def create_orchestrator_and_subagents() -> tuple[Agent, list[Agent]]:
    """Create orchestrator + sub-agents using can_call (Hackapizza-style)."""
    client = OpenAILikeClient(
        api_key=REGOLO_API_KEY,
        model=REGOLO_MODEL,
        base_url=REGOLO_BASE_URL,
    )

    # Sub-agent 1: coding assistant (has execute_python tool)
    coding_assistant = create_coding_agent()

    # Sub-agent 2: general assistant (has quick_lookup tool)
    general_assistant = Agent(
        name="general_assistant",
        client=client,
        system_prompt=GENERAL_ASSISTANT_PROMPT,
        tools=[quick_lookup],
    )

    sub_agents = [coding_assistant, general_assistant]

    # Orchestrator: no tools, delegates via can_call
    orchestrator = Agent(
        name="orchestrator",
        client=client,
        system_prompt=ORCHESTRATOR_PROMPT,
        stateless=False,
        tools=[],  # Orchestrator delegates, does not use tools directly
    )
    orchestrator.can_call(sub_agents)

    return orchestrator, sub_agents


def run_orchestrator(orchestrator: Agent, question: str) -> str:
    """Run orchestrator on a question (with optional tracing)."""
    def _run() -> str:
        response = orchestrator.run(question)
        return response.text if response else ""

    if _tracer is not None:
        with _tracer.start_as_current_span("orchestrator.answer") as span:
            span.set_attribute("question", question[:500])
            result = _run()
            span.set_attribute("response_length", len(result))
            return result
    return _run()


def main() -> None:
    orchestrator, sub_agents = create_orchestrator_and_subagents()
    print("Orchestrator-subagents system ready (can_call pattern).")
    print("Sub-agents:", [a.name for a in sub_agents])
    if _tracer:
        print("Monitoring enabled. Check dashboard for: orchestrator.answer -> [coding_assistant, general_assistant]")
    else:
        print("Monitoring disabled. Set DATAPIZZA_MONITORING_API_KEY and DATAPIZZA_PROJECT_ID to verify traces.")
    print()

    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
        print(run_orchestrator(orchestrator, question))
    else:
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
                answer = run_orchestrator(orchestrator, question)
                print(f"\nAssistant: {answer}\n")
            except Exception as e:
                print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
