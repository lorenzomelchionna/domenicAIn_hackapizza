"""Pydantic models for game data validation between agents."""
from pydantic import BaseModel, Field


class Ingredient(BaseModel):
    """An ingredient with quantity."""
    name: str
    quantity: int = Field(gt=0)


class Recipe(BaseModel):
    """A recipe for the draft menu."""
    name: str
    ingredients: list[Ingredient] = Field(default_factory=list)
    preparationTimeMs: int = Field(default=0, ge=0)
    prestige: int = Field(default=0, ge=0)


class MenuItem(BaseModel):
    """A menu item with name and price."""
    name: str
    price: float = Field(gt=0)


class SuggestedBid(BaseModel):
    """Analyst output: recommended bid price per ingredient."""
    ingredient: str
    price: float = Field(gt=0, description="Price per unit")


class AuctionBid(BaseModel):
    """Input for closed_bid auction."""
    ingredient: str
    bid: float = Field(gt=0, description="Bid price per unit")
    quantity: int = Field(gt=0)


class ActualBid(BaseModel):
    """Auction result for an ingredient."""
    ingredient: str
    price: float = Field(ge=0)
    success: bool


class PendingClient(BaseModel):
    """A client waiting to be served."""
    client_id: str
    clientName: str = ""
    orderText: str = ""
    intolerances: list[str] = Field(default_factory=list)
