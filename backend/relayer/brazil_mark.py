"""Brazil mark engine: ICE + β_const anchor with separate book EMA."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from relayer.config import RelayerConfig
from relayer.engine import beta, clamp_bps, impact_bid_ask, median3
from relayer.models import Mode, OrderBookSnapshot, best_bid_ask


@dataclass
class BrazilMarkState:
    ts: float
    mark: float
    oracle: float
    basis_ema: float  # EMA of (book_mid − structural anchor)


@dataclass
class BrazilMarkOutput:
    ts: float
    mode: Mode
    mark: float
    oracle: float
    c1: float  # ICE oracle + β_const (structural anchor)
    c2: float  # c1 + basis_ema
    c3: float  # book mid / trade median
    basis_ema: float
    basis_structural: float
    basis_traded: float  # book_mid − c1 (instantaneous residual)
    impact_bid: float
    impact_ask: float
    mid: float
    best_bid: float
    best_ask: float
    last_trade: float
    ice_anchor: float


def update_brazil_mark(
    cfg: RelayerConfig,
    prev: BrazilMarkState,
    now_ts: float,
    book: OrderBookSnapshot,
    *,
    ice_oracle: float,
    beta_const: float,
    mode: Mode,
) -> BrazilMarkOutput:
    dt = max(0.001, now_ts - prev.ts)
    b_mark = beta(dt, cfg.tau_mark)

    best_bid, best_ask = best_bid_ask(book)
    mid = (best_bid + best_ask) / 2.0
    impact_bid, impact_ask = impact_bid_ask(book, cfg.impact_notional_q)

    c1 = ice_oracle + beta_const
    basis_traded = mid - c1
    basis_ema = b_mark * prev.basis_ema + (1.0 - b_mark) * basis_traded

    c2 = c1 + basis_ema
    c3 = median3(best_bid, best_ask, book.last_trade)
    mark_raw = median3(c1, c2, c3)
    mark = clamp_bps(mark_raw, prev.mark, cfg.clamp_bps)

    # Brazil oracle tracks structural anchor; mark medians in book discovery
    oracle = clamp_bps(c1, prev.oracle, cfg.clamp_bps)

    return BrazilMarkOutput(
        ts=now_ts,
        mode=mode,
        mark=mark,
        oracle=oracle,
        c1=c1,
        c2=c2,
        c3=c3,
        basis_ema=basis_ema,
        basis_structural=beta_const,
        basis_traded=basis_traded,
        impact_bid=impact_bid,
        impact_ask=impact_ask,
        mid=mid,
        best_bid=best_bid,
        best_ask=best_ask,
        last_trade=book.last_trade,
        ice_anchor=ice_oracle,
    )
