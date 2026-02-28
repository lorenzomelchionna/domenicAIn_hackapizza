"""Hackapizza multi-agent system."""
from .restaurant_manager import create_restaurant_manager
from .diplomatico import create_diplomatico
from .menu_decider_pre_bid import create_menu_decider_pre_bid
from .menu_decider_post_bid import create_menu_decider_post_bid
from .auction_broker import create_auction_broker
from .market_broker import create_market_broker
from .maitre import create_maitre


def create_all_agents(client, mcp_client, phase_getter, state_getter=None):
    """Create all agents with proper tool assignment and phase-gated delegation."""
    from src.tools.game_tools import create_game_tools
    from src.agents.phase_gate import wire_phase_gated_agents

    _, tools_by_name = create_game_tools(mcp_client, state_getter)

    diplomatico = create_diplomatico(client, [tools_by_name["send_message"]])
    menu_decider_pre_bid = create_menu_decider_pre_bid(
        client,
        [tools_by_name["get_recipes"], tools_by_name["save_draft_menu"]],
    )
    menu_decider_post_bid = create_menu_decider_post_bid(
        client,
        [tools_by_name["save_menu"], tools_by_name["get_recipes"], tools_by_name["get_inventory"], tools_by_name["get_draft_menu"]],
    )
    auction_broker = create_auction_broker(client, [tools_by_name["closed_bid"], tools_by_name["get_draft_menu"]])
    market_broker = create_market_broker(
        client,
        [
            tools_by_name["create_market_entry"],
            tools_by_name["execute_transaction"],
            tools_by_name["delete_market_entry"],
        ],
    )
    maitre = create_maitre(
        client,
        [tools_by_name["prepare_dish"], tools_by_name["serve_dish"]],
    )

    # MVP: only core loop agents active (Market Broker + Diplomatico disabled)
    sub_agents = [
        menu_decider_pre_bid,
        auction_broker,
        menu_decider_post_bid,
        maitre,
    ]

    # Create RM with its own tools (no can_call — we use phase-gated wiring instead)
    restaurant_manager = create_restaurant_manager(client, [], [tools_by_name["update_restaurant_is_open"]])

    # Wire sub-agents as phase-gated tools on the RM
    # RM can "see" all agents, but calling one in the wrong phase returns an error
    wire_phase_gated_agents(restaurant_manager, sub_agents, phase_getter)

    return restaurant_manager, sub_agents
