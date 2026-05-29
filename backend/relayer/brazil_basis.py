"""Brazil basis model: ICE anchor + FX + seasonality."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class BrazilBasisConfig:
    beta0: float = 0.023344
    beta1: float = -0.190676
    fx_ref: float = 5.4984
    max_abs_basis: float = 0.08
    month_effects: tuple = (
        -0.01150,
        -0.01534,
        0.00159,
        0.00138,
        0.01533,
        0.01156,
        0.01477,
        0.00763,
        0.00130,
        -0.00455,
        -0.01164,
        -0.00900,
    )


def zfx(fx_usdbrl: float, fx_ref: float) -> float:
    if fx_ref <= 0:
        return 0.0
    return (fx_usdbrl - fx_ref) / fx_ref


def month_index(ts: float | None = None) -> int:
    t = time.gmtime(ts or time.time())
    return t.tm_mon - 1  # 0..11


def predict_basis_usd_lb(fx_usdbrl: float, cfg: BrazilBasisConfig, ts: float | None = None) -> float:
    m = month_index(ts)
    season = cfg.month_effects[m]
    basis = cfg.beta0 + cfg.beta1 * zfx(fx_usdbrl, cfg.fx_ref) + season
    return max(-cfg.max_abs_basis, min(cfg.max_abs_basis, basis))


def brazil_mark_usd_lb(ice_usd_lb: float, fx_usdbrl: float, cfg: BrazilBasisConfig, ts: float | None = None) -> float:
    return ice_usd_lb + predict_basis_usd_lb(fx_usdbrl, cfg, ts)


def simulate_fx_usdbrl(prev: float | None = None) -> float:
    """TEST-only synthetic USD/BRL."""
    import random

    base = prev if prev is not None else 5.50
    nxt = base + random.uniform(-0.015, 0.015)
    return max(4.80, min(6.20, nxt))


def simulate_fx_usdaud(prev: float | None = None) -> float:
    """TEST-only synthetic AUD/USD (USD per 1 AUD)."""
    import random

    base = prev if prev is not None else 0.65
    nxt = base + random.uniform(-0.002, 0.002)
    return max(0.55, min(0.80, nxt))
