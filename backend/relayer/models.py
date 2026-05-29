from dataclasses import dataclass
from typing import List, Literal, Optional, Tuple


Mode = Literal["external", "internal_fallback"]


@dataclass
class BookLevel:
    price: float
    size: float  # base size


@dataclass
class OrderBookSnapshot:
    bids: List[BookLevel]  # sorted high -> low
    asks: List[BookLevel]  # sorted low -> high
    last_trade: float


@dataclass
class ExternalPriceTick:
    price: float
    ts: float


@dataclass
class RelayerState:
    ts: float
    oracle: float
    mark: float
    basis_ema: float


@dataclass
class RelayerOutput:
    ts: float
    mode: Mode
    oracle: float
    mark: float
    c1: float
    c2: float
    c3: float
    ipd: float
    impact_bid: float
    impact_ask: float
    mid: float
    best_bid: float
    best_ask: float
    last_trade: float
    external_price: Optional[float]


def best_bid_ask(book: OrderBookSnapshot) -> Tuple[float, float]:
    return book.bids[0].price, book.asks[0].price
