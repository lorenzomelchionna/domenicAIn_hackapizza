"""System prompts for Hackapizza agents."""
from .restaurant_manager import SYSTEM_PROMPT as RESTAURANT_MANAGER_PROMPT
from .diplomatico import SYSTEM_PROMPT as DIPLOMATICO_PROMPT
from .menu_decider_pre_bid import SYSTEM_PROMPT as MENU_DECIDER_PRE_BID_PROMPT
from .menu_decider_post_bid import SYSTEM_PROMPT as MENU_DECIDER_POST_BID_PROMPT
from .auction_broker import SYSTEM_PROMPT as AUCTION_BROKER_PROMPT
from .market_broker import SYSTEM_PROMPT as MARKET_BROKER_PROMPT
from .maitre import SYSTEM_PROMPT as MAITRE_PROMPT
from .analyst import SYSTEM_PROMPT as ANALYST_PROMPT
from .pricing_analyst import SYSTEM_PROMPT as PRICING_ANALYST_PROMPT

__all__ = [
    "RESTAURANT_MANAGER_PROMPT",
    "DIPLOMATICO_PROMPT",
    "MENU_DECIDER_PRE_BID_PROMPT",
    "MENU_DECIDER_POST_BID_PROMPT",
    "AUCTION_BROKER_PROMPT",
    "MARKET_BROKER_PROMPT",
    "MAITRE_PROMPT",
    "ANALYST_PROMPT",
    "PRICING_ANALYST_PROMPT",
]
