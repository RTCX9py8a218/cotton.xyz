"""Brazil structural basis — re-exports origin loader for backward compatibility."""

from __future__ import annotations

from dataclasses import dataclass

from relayer.origin_constant import OriginConstantConfig, load_origin_config

DEFAULT_BETA_CONST_USD_LB = 0.0417


@dataclass(frozen=True)
class BrazilConstantConfig:
    """Governance-set structural Brazil premium vs ICE (USD/lb)."""

    beta_const_usd_lb: float
    calibration_window_days: int = 504
    method: str = "median"
    max_abs_basis: float = 0.08


def load_constant_config() -> BrazilConstantConfig:
    cfg = load_origin_config("BRAZIL")
    return BrazilConstantConfig(
        beta_const_usd_lb=cfg.beta_const_usd_lb,
        calibration_window_days=cfg.calibration_window_days,
        method=cfg.method,
        max_abs_basis=cfg.max_abs_basis,
    )


def clamp_basis(basis: float, max_abs: float) -> float:
    return max(-max_abs, min(max_abs, basis))


def apply_constant_basis(ice_usd_lb: float, cfg: BrazilConstantConfig) -> tuple[float, float]:
    """Returns (mark_usd_lb, basis_used). β_const is governance-set — not clamped here."""
    basis = cfg.beta_const_usd_lb
    return ice_usd_lb + basis, basis


def brazil_mark_from_relayer(ice_mark: float, ice_oracle: float, cfg: BrazilConstantConfig) -> tuple[float, float, float]:
    """Apply constant to relayer ICE mark/oracle (carries EMA fallback from US leg)."""
    mark, basis = apply_constant_basis(ice_mark, cfg)
    oracle, _ = apply_constant_basis(ice_oracle, cfg)
    return mark, oracle, basis
