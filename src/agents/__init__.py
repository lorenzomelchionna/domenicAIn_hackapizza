"""Hackapizza multi-agent system."""
from .restaurant_manager import create_restaurant_manager
from .diplomatico import create_diplomatico
from .menu_decider_pre_bid import create_menu_decider_pre_bid
from .menu_decider_post_bid import create_menu_decider_post_bid
from .auction_broker import create_auction_broker
from .market_broker import create_market_broker
from .maitre import create_maitre


def create_all_agents(client, mcp_client, phase_getter, state_getter=None):
    """Create all agents with proper tool assignment and can_call wiring."""
    from src.tools.game_tools import create_game_tools

    _, tools_by_name = create_game_tools(mcp_client, state_getter)

    diplomatico = create_diplomatico(client, [tools_by_name["send_message"]])
    menu_decider_pre_bid = create_menu_decider_pre_bid(
        client,
        [tools_by_name["save_menu"], tools_by_name["get_recipes"], tools_by_name["get_inventory"]],
    )
    menu_decider_post_bid = create_menu_decider_post_bid(
        client,
        [tools_by_name["save_menu"], tools_by_name["get_recipes"], tools_by_name["get_inventory"]],
    )
    auction_broker = create_auction_broker(client, [tools_by_name["closed_bid"]])
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

    sub_agents = [
        diplomatico,
        menu_decider_pre_bid,
        menu_decider_post_bid,
        auction_broker,
        market_broker,
        maitre,
    ]
    restaurant_manager = create_restaurant_manager(client, sub_agents, [tools_by_name["update_restaurant_is_open"]])

    return restaurant_manager, sub_agents
