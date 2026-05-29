import random
from typing import Optional

try:
    from .models import BookLevel, ExternalPriceTick, OrderBookSnapshot
except ImportError:
    from models import BookLevel, ExternalPriceTick, OrderBookSnapshot


def make_book(mid: float, spread_bps: float = 8.0, levels: int = 14) -> OrderBookSnapshot:
    spread = mid * (spread_bps / 10_000.0)
    best_bid = mid - spread / 2.0
    best_ask = mid + spread / 2.0

    bids = []
    asks = []
    for i in range(levels):
        step = mid * (2.0 / 10_000.0) * i
        bid_px = best_bid - step
        ask_px = best_ask + step
        size = 80 + i * 25 + random.uniform(-5, 5)
        bids.append(BookLevel(price=bid_px, size=max(1.0, size)))
        asks.append(BookLevel(price=ask_px, size=max(1.0, size)))

    last_trade = mid + random.uniform(-spread / 3.0, spread / 3.0)
    return OrderBookSnapshot(bids=bids, asks=asks, last_trade=last_trade)


def make_origin_book(
    anchor_mid: float,
    trader_residual_basis: float = 0.0,
    spread_bps: float = 10.0,
    levels: int = 14,
) -> OrderBookSnapshot:
    """
    Origin-specific book centered on structural anchor + trader residual basis.
    Residual simulates premium/discount discovery on origin/USDC pairs.
    """
    mid = max(0.01, anchor_mid + trader_residual_basis)
    mid += random.uniform(-0.008, 0.008)
    return make_book(mid=mid, spread_bps=spread_bps, levels=levels)


def make_brazil_book(
    anchor_mid: float,
    trader_residual_basis: float = 0.0,
    spread_bps: float = 10.0,
    levels: int = 14,
) -> OrderBookSnapshot:
    return make_origin_book(
        anchor_mid=anchor_mid,
        trader_residual_basis=trader_residual_basis,
        spread_bps=spread_bps,
        levels=levels,
    )


def fake_external_price(now_ts: float, base: float) -> Optional[ExternalPriceTick]:
    # Simulate external feed unavailable periodically (e.g., exchange closed).
    cycle = int(now_ts) % 32
    if cycle >= 20:
        return None
    noise = random.uniform(-0.08, 0.08)
    return ExternalPriceTick(price=base + noise, ts=now_ts)
