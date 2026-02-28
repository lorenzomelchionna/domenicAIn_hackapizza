# Plan Mode Prompt: Hackapizza 2.0 Multi-Agent Restaurant System

## Context & Sources

Use the following as primary references:

1. **Domain knowledge**: `knowledge/hackapizza_flow.html` — game mechanics, phases, operations matrix, SSE events, HTTP endpoints, MCP tools.
2. **Framework**: `datapizza_ai_practice/` — datapizza-ai patterns, especially `06_multi_agent/workflow.py` (orchestrator + sub-agents via `can_call()`), system prompts in separate files, and tool usage.

## Objective

Design and implement a first working version of a hierarchical multi-agent system that manages a Hackapizza 2.0 restaurant. The system must be a minimal but functional skeleton, easy to extend with sub-agents and new behaviors.

## Architecture Requirements

### 1. Hierarchical Multi-Agent Structure

**Top level — Restaurant Manager (Orchestrator)**

- Single orchestrator agent.
- Responsibilities:
  - Opening and closing the restaurant (`update_restaurant_is_open`), in this phase restaurant is always open.
  - Phase-based dispatch: routes work to the right agents depending on the current phase (`speaking`, `closed_bid`, `waiting`, `serving`, `stopped`).
  - Coordination of sub-agents and overall flow.
- Uses `stateless=False` for memory across turns.
- Uses `can_call()` to delegate to the 6 sub-agents.

**Sub-agents (6 agents)**

| Agent | Role | Phase(s) Active | Primary Responsibility |
|-------|------|-----------------|------------------------|
| **Diplomatico** | Diplomacy & collaboration | speaking (primarily) | For now: send a message to all restaurants asking for potential collaboration. Uses `send_message` (or equivalent broadcast). |
| **Menu Decider (Pre-Bid)** | Initial menu planning | speaking, closed_bid | Decide menu based on: balance, recipes, inventory, strategy. Output: draft menu (recipes + prices). |
| **Menu Decider (Post-Bid)** | Final menu | waiting | Finalize menu after auction results. Adapt to actual inventory. Uses `save_menu`. |
| **Auction Broker** | Supplier procurement | closed_bid | Interface with supplier via `closed_bid`. Given strategy and menu, compute and submit bids. |
| **Market Broker** | Inter-restaurant trading | speaking, closed_bid, waiting, serving | Interface with other restaurants. Create/execute/delete market entries. Always active in non-stopped phases. |
| **Maitre** | Customer service | serving | Handle customer orders, interpret `orderText`, check intolerances, call `prepare_dish` and `serve_dish`. |

### 2. Phase-to-Agent Mapping

- **speaking**: Diplomatico, Menu Decider (Pre-Bid), Market Broker
- **closed_bid**: Menu Decider (Pre-Bid), Auction Broker, Market Broker
- **waiting**: Menu Decider (Post-Bid), Market Broker
- **serving**: Maitre, Market Broker
- **stopped**: Read-only; no action agents

## Technical Requirements

1. **datapizza-ai**
   - Use `Agent`, `can_call()`, `OpenAILikeClient` (Regolo.ai).
   - MCP tools exposed by the game server as the main action interface.

2. **System prompts**
   - One file per agent under `prompts/`:
     - `restaurant_manager.py`
     - `diplomatico.py`
     - `menu_decider_pre_bid.py`
     - `menu_decider_post_bid.py`
     - `auction_broker.py`
     - `market_broker.py`
     - `maitre.py`

3. **Atomic tasks**
   - Each agent has a small, well-defined responsibility.
   - Tasks are single-purpose and composable.
   - Orchestrator delegates via clear, phase-specific instructions.

4. **SSE event loop**
   - Connect to `GET /events/:restaurantId`.
   - React to `game_started`, `game_phase_changed`, `client_spawned`, `preparation_complete`, `new_message`.
   - On phase change, trigger the appropriate agents.

5. **State management**
   - Shared state (balance, inventory, menu, reputation, current phase, clients).
   - State updated from HTTP endpoints and SSE events.
   - Passed to agents as context when delegating.

## Extensibility

- Modular agent definitions so new sub-agents can be added later.
- Clear interfaces between orchestrator and sub-agents.
- Config-driven phase-to-agent mapping where possible.
- Placeholder hooks for future sub-agents (e.g., strategy engine, client handler refinements).

## Deliverables (Skeleton)

1. **Project structure**
    src/
        agents/
            restaurant_manager.py
            diplomatico.py
            menu_decider_pre_bid.py
            menu_decider_post_bid.py
            auction_broker.py
            market_broker.py
            maitre.py
        prompts/
            restaurant_manager.py
            diplomatico.py
            ...
        state/
            game_state.py
        sse/
            listener.py
        main.py
2. **Main loop**
   - Initialize SSE connection, state, and agents.
   - Event loop: on SSE event → update state → if phase change → call Restaurant Manager with current phase and context → Restaurant Manager delegates to sub-agents.

3. **MCP integration**
   - Expose game MCP tools to agents (via datapizza-ai MCP client or equivalent).
   - Respect phase constraints (e.g., no `closed_bid` in speaking, no `save_menu` in serving).

## Constraints

- No human-in-the-loop.
- Respect rate limits (429).
- Ingredients expire at end of turn; avoid waste.
- Always check intolerances before serving.
- In serving phase, `update_restaurant_is_open` can only close, not reopen.

## Success Criteria for First Version

- System runs end-to-end: SSE connection, phase handling, agent invocation.
- Restaurant Manager correctly delegates by phase.
- Each of the 6 agents performs its minimal task (Diplomatico sends a message, Menu Deciders produce/update menu, Auction Broker submits bids, Market Broker manages entries, Maitre handles at least one order).
- Code is structured for easy extension (new agents, richer logic, sub-agents).
   