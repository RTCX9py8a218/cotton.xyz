"""Governance-set structural basis (β_const) per origin."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

CONSTANT_PARAMS_PATH = (
    Path(__file__).resolve().parents[1] / "analysis" / "data" / "constant_params.json"
)

DEFAULT_BETA: Dict[str, float] = {
    "BRAZIL": 0.0902,
    "AUSTRALIA": 0.0280,  # ~+280 pts; industry ICE+basis guides
}


@dataclass(frozen=True)
class OriginConstantConfig:
    origin: str
    beta_const_usd_lb: float
    calibration_window_days: int = 504
    method: str = "median"
    max_abs_basis: float = 0.08
    source: str = ""


def load_origin_config(origin: str) -> OriginConstantConfig:
    origin_key = origin.upper()
    fallback = DEFAULT_BETA.get(origin_key, 0.0)

    if CONSTANT_PARAMS_PATH.exists():
        try:
            data = json.loads(CONSTANT_PARAMS_PATH.read_text(encoding="utf-8"))
            origins = data.get("origins") or {}
            if origin_key in origins:
                row = origins[origin_key]
                return OriginConstantConfig(
                    origin=origin_key,
                    beta_const_usd_lb=float(row["beta_const_usd_lb"]),
                    calibration_window_days=int(row.get("calibration_window_days", 504)),
                    method=str(row.get("method", "median")),
                    max_abs_basis=float(row.get("max_abs_basis", 0.08)),
                    source=str(row.get("source", "")),
                )
            # Legacy flat file (Brazil-only v3)
            if origin_key == "BRAZIL" and "beta_const_usd_lb" in data:
                return OriginConstantConfig(
                    origin=origin_key,
                    beta_const_usd_lb=float(data["beta_const_usd_lb"]),
                    calibration_window_days=int(data.get("calibration_window_days", 504)),
                    method=str(data.get("method", "median")),
                    max_abs_basis=float(data.get("max_abs_basis", 0.08)),
                    source=str(data.get("source", "")),
                )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            pass

    return OriginConstantConfig(
        origin=origin_key,
        beta_const_usd_lb=fallback,
        source="fallback default",
    )
