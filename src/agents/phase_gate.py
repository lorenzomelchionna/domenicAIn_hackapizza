"""Phase-gated agent wrapper. Ensures sub-agents can only be invoked in allowed phases."""
from typing import Any, Callable, cast

from datapizza.agents import Agent
from datapizza.agents.agent import StepResult
from datapizza.tools import Tool

# Phase-to-allowed-agents mapping (source of truth)
PHASE_ALLOWED_AGENTS: dict[str, list[str]] = {
    "speaking": ["menu_decider_pre_bid"],
    "closed_bid": ["auction_broker"],
    "waiting": ["menu_decider_post_bid"],
    "serving": ["maitre"],
    "stopped": [],
}


def _build_allowed_phases(agent_name: str) -> list[str]:
    """Invert PHASE_ALLOWED_AGENTS: for a given agent, which phases allow it?"""
    return [phase for phase, agents in PHASE_ALLOWED_AGENTS.items() if agent_name in agents]


def make_phase_gated_tool(agent: Agent, phase_getter: Callable[[], str]) -> Tool:
    """Create a Tool from a sub-agent that checks the current phase before running.
    
    If the agent is called in a phase where it's not allowed, returns an error
    message to the orchestrator instead of running the agent.
    """
    allowed_phases = _build_allowed_phases(agent.name)

    async def phase_gated_invoke(input_task: str) -> str:
        current_phase = phase_getter()
        if current_phase not in allowed_phases:
            return (
                f"ERROR: Agent '{agent.name}' cannot be called in phase '{current_phase}'. "
                f"Allowed phases: {allowed_phases}. "
                f"Call a different agent appropriate for this phase."
            )
        result = cast(StepResult, await agent.a_run(input_task))
        return result.text if result else "No response"

    return Tool(
        func=phase_gated_invoke,
        name=agent.name,
        description=f"Sub-agent: {agent.name}. Allowed phases: {', '.join(allowed_phases)}. {agent.__doc__ or ''}",
    )


def wire_phase_gated_agents(
    orchestrator: Agent,
    sub_agents: list[Agent],
    phase_getter: Callable[[], str],
) -> None:
    """Wire sub-agents to the orchestrator with phase gates.
    
    Replaces the normal can_call() mechanism with phase-aware tool wrappers.
    If the RM tries to call an agent in the wrong phase, it gets a clear error.
    """
    gated_tools = [make_phase_gated_tool(a, phase_getter) for a in sub_agents]
    # Add gated tools to orchestrator's tool list (don't use can_call, we're replacing it)
    for t in gated_tools:
        orchestrator._tools.append(t)
