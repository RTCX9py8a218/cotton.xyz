"""Hybrid Brazil mark: rolling FX model + CEPEA override when fresh."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from relayer.brazil_basis import BrazilBasisConfig, predict_basis_usd_lb, zfx


@dataclass(frozen=True)
class HybridConfig:
    """Production / backtest hybrid oracle settings."""

    train_window_days: int = 504  # ~2 years trailing recalibration
    cepea_max_age_s: float = 86_400.0  # 24h freshness window
    max_abs_basis: float = 0.08
    blend_cepea_weight: float = 1.0  # 1.0 = full CEPEA override when fresh


@dataclass
class HybridState:
    """Runtime CEPEA freshness tracking (relayer)."""

    basis_cepea: Optional[float] = None
    cepea_ts: Optional[float] = None
    basis_model: float = 0.0


def clamp_basis(basis: float, max_abs: float) -> float:
    return max(-max_abs, min(max_abs, basis))


def cepea_is_fresh(now_ts: float, cepea_ts: Optional[float], max_age_s: float) -> bool:
    if cepea_ts is None:
        return False
    return (now_ts - cepea_ts) <= max_age_s


def hybrid_basis(
    *,
    basis_model: float,
    basis_cepea: Optional[float],
    fresh: bool,
    cfg: HybridConfig,
) -> tuple[float, str]:
    """
    Returns (basis_usd_lb, source_tag).
    source_tag: 'cepea' | 'model' | 'blend'
    """
    model = clamp_basis(basis_model, cfg.max_abs_basis)
    if not fresh or basis_cepea is None:
        return model, "model"

    obs = clamp_basis(basis_cepea, cfg.max_abs_basis)
    w = cfg.blend_cepea_weight
    if w >= 1.0:
        return obs, "cepea"
    if w <= 0.0:
        return model, "model"
    blended = clamp_basis(w * obs + (1.0 - w) * model, cfg.max_abs_basis)
    return blended, "blend"


def hybrid_mark_usd_lb(
    ice_usd_lb: float,
    *,
    basis_model: float,
    basis_cepea: Optional[float],
    fresh: bool,
    cfg: HybridConfig,
) -> tuple[float, float, str]:
    """Returns (mark, basis_used, source)."""
    basis, source = hybrid_basis(
        basis_model=basis_model,
        basis_cepea=basis_cepea,
        fresh=fresh,
        cfg=cfg,
    )
    return ice_usd_lb + basis, basis, source


def params_to_brazil_config(params) -> BrazilBasisConfig:
    """Convert analysis BasisParams → relayer BrazilBasisConfig."""
    return BrazilBasisConfig(
        beta0=params.beta0,
        beta1=params.beta1,
        fx_ref=params.fx_ref,
        max_abs_basis=params.max_abs_basis,
        month_effects=tuple(params.month_effects),
    )


def predict_model_basis(
    fx_usdbrl: float,
    cfg: BrazilBasisConfig,
    ts: Optional[float] = None,
) -> float:
    return predict_basis_usd_lb(fx_usdbrl, cfg, ts)
