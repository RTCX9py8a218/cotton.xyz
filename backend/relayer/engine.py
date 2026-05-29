import math
from typing import Optional

try:
    from .config import RelayerConfig
    from .models import (
        ExternalPriceTick,
        OrderBookSnapshot,
        RelayerOutput,
        RelayerState,
        best_bid_ask,
    )
except ImportError:
    # Allows running as a direct script in MVP workflows.
    from config import RelayerConfig
    from models import (
        ExternalPriceTick,
        OrderBookSnapshot,
        RelayerOutput,
        RelayerState,
        best_bid_ask,
    )


def clamp_bps(raw: float, prev: float, bps: float) -> float:
    k = bps / 10_000.0
    lo = prev * (1.0 - k)
    hi = prev * (1.0 + k)
    return max(lo, min(raw, hi))


def beta(dt_s: float, tau_s: float) -> float:
    if dt_s <= 0:
        return 1.0
    return math.exp(-dt_s / tau_s)


def median3(a: float, b: float, c: float) -> float:
    return sorted([a, b, c])[1]


def _vwap_at_notional(levels, target_notional: float) -> float:
    # levels: list[BookLevel] with price and base size
    rem = target_notional
    quote_used = 0.0
    base_acc = 0.0
    for lv in levels:
        lv_quote = lv.price * lv.size
        take_quote = min(rem, lv_quote)
        take_base = take_quote / lv.price
        quote_used += take_quote
        base_acc += take_base
        rem -= take_quote
        if rem <= 1e-9:
            break
    if base_acc <= 1e-12:
        # no depth available; caller should guard upstream
        return levels[0].price
    return quote_used / base_acc


def impact_bid_ask(book: OrderBookSnapshot, q: float) -> tuple[float, float]:
    impact_bid = _vwap_at_notional(book.bids, q)
    impact_ask = _vwap_at_notional(book.asks, q)
    return impact_bid, impact_ask


def ipd(oracle_prev: float, impact_bid: float, impact_ask: float) -> float:
    up = max(impact_bid - oracle_prev, 0.0)
    down = max(oracle_prev - impact_ask, 0.0)
    return up - down


def external_is_fresh(
    external_tick: Optional[ExternalPriceTick], now_ts: float, max_stale_s: float
) -> bool:
    if external_tick is None:
        return False
    return (now_ts - external_tick.ts) <= max_stale_s


def update_relayer(
    cfg: RelayerConfig,
    prev: RelayerState,
    now_ts: float,
    book: OrderBookSnapshot,
    external_tick: Optional[ExternalPriceTick],
) -> RelayerOutput:
    dt = max(0.001, now_ts - prev.ts)
    b_oracle = beta(dt, cfg.tau_oracle)
    b_mark = beta(dt, cfg.tau_mark)

    best_bid, best_ask = best_bid_ask(book)
    mid = (best_bid + best_ask) / 2.0
    impact_bid, impact_ask = impact_bid_ask(book, cfg.impact_notional_q)
    ipd_val = ipd(prev.oracle, impact_bid, impact_ask)

    if external_is_fresh(external_tick, now_ts, cfg.max_stale_external_s):
        mode = "external"
        oracle_raw = external_tick.price
        external_price = external_tick.price
    else:
        mode = "internal_fallback"
        x = prev.oracle + ipd_val
        oracle_raw = b_oracle * prev.oracle + (1.0 - b_oracle) * x
        external_price = None

    oracle = clamp_bps(oracle_raw, prev.oracle, cfg.clamp_bps)

    basis = mid - oracle
    basis_ema = b_mark * prev.basis_ema + (1.0 - b_mark) * basis

    c1 = oracle
    c2 = oracle + basis_ema
    c3 = median3(best_bid, best_ask, book.last_trade)
    mark_raw = median3(c1, c2, c3)
    mark = clamp_bps(mark_raw, prev.mark, cfg.clamp_bps)

    return RelayerOutput(
        ts=now_ts,
        mode=mode,  # type: ignore[arg-type]
        oracle=oracle,
        mark=mark,
        c1=c1,
        c2=c2,
        c3=c3,
        ipd=ipd_val,
        impact_bid=impact_bid,
        impact_ask=impact_ask,
        mid=mid,
        best_bid=best_bid,
        best_ask=best_ask,
        last_trade=book.last_trade,
        external_price=external_price,
    )
