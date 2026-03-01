"""Hackapizza multi-agent system."""
from .restaurant_manager import create_restaurant_manager
from .diplomatico import create_diplomatico
from .menu_decider_pre_bid import create_menu_decider_pre_bid
from .menu_decider_post_bid import create_menu_decider_post_bid
from .auction_broker import create_auction_broker
from .market_broker import create_market_broker
from .maitre import create_maitre
from .analyst import create_analyst


def create_all_agents(client, mcp_client, phase_getter, state_getter=None, db_path=None):
    """Create all agents with proper tool assignment and can_call wiring.
    
    Args:
        client: LLM client
        mcp_client: MCP client for game tools
        phase_getter: Function to get current game phase
        state_getter: Function to get shared game state
        db_path: Path to SQLite database for market intelligence (required for analyst)
    """
    from src.tools.game_tools import create_game_tools
    from src.tools.analyst_tools import create_analyst_tools

    _, tools_by_name = create_game_tools(mcp_client, state_getter)

    diplomatico = create_diplomatico(client, [tools_by_name["send_message"]])
    menu_decider_pre_bid = create_menu_decider_pre_bid(
        client,
        [tools_by_name["get_recipes"], tools_by_name["save_draft_menu"]],
    )
    menu_decider_post_bid = create_menu_decider_post_bid(
        client,
        [
            tools_by_name["save_menu"],
            tools_by_name["get_recipes"],
            tools_by_name["get_inventory"],
            tools_by_name["get_draft_menu"],
            tools_by_name["calculate_suggested_prices"],
        ],
    )
    auction_broker = create_auction_broker(client, [
        tools_by_name["closed_bid"],
        tools_by_name["get_draft_menu"],
        tools_by_name["get_suggested_bids"],
        tools_by_name["save_actual_bids"],
    ])
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
        [tools_by_name["prepare_dish"], tools_by_name["serve_dish"], tools_by_name["get_pending_clients"]],
    )

    analyst = None
    if db_path:
        analyst_tools_list, _ = create_analyst_tools(db_path, state_getter)
        analyst = create_analyst(
            client,
            analyst_tools_list + [
                tools_by_name["save_suggested_bids"],
                tools_by_name["get_draft_menu"],
            ],
        )

    # MVP: Market Broker excluded from can_call — only core loop agents active
    sub_agents = [
        diplomatico,
        menu_decider_pre_bid,
        analyst,
        menu_decider_post_bid,
        auction_broker,
        # market_broker,  # DISABLED for MVP
        maitre,
    ]
    
    # Filter out None agents (e.g., analyst when db_path not provided)
    sub_agents = [a for a in sub_agents if a is not None]
    
    restaurant_manager = create_restaurant_manager(client, sub_agents, [tools_by_name["update_restaurant_is_open"]])

    return restaurant_manager, sub_agents

