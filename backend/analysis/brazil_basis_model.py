#!/usr/bin/env python3
"""
Brazil basis research scaffold (TEST).

Computes observed basis vs ICE and fits a simple FX + seasonality model.

Usage:
  python3 backend/analysis/brazil_basis_model.py

Notes:
- Uses synthetic/demo series when historical CSV files are absent.
- Replace load_series() with CEPEA + ICE + FX CSV ingestion for production calibration.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple


@dataclass
class DailyRow:
    ts: int
    month: int
    ice_usd_lb: float
    cepea_brl_lp: float
    fx_usdbrl: float

    @property
    def cepea_usd_lb(self) -> float:
        return self.cepea_brl_lp / self.fx_usdbrl

    @property
    def basis_obs(self) -> float:
        return self.cepea_usd_lb - self.ice_usd_lb


@dataclass
class BasisParams:
    beta0: float
    beta1: float
    month_effects: List[float]  # index 1..12
    fx_ref: float
    max_abs_basis: float = 0.08  # 8 cents/lb clamp


def generate_demo_series(n: int = 520) -> List[DailyRow]:
    """Synthetic series mimicking CEPEA/ICE/FX co-movement for pipeline testing."""
    rows: List[DailyRow] = []
    ice = 0.78
    fx = 5.10
    cepea_brl = ice * fx * 1.05

    for i in range(n):
        month = (i // 30) % 12 + 1
        # weak BRL trend + noise
        fx += 0.0015 + (0.002 if i % 90 < 45 else -0.001)
        fx = max(4.8, min(6.2, fx))

        ice += 0.0002 * math.sin(i / 17.0) + (0.0005 if i % 60 == 0 else 0)
        ice = max(0.62, min(0.95, ice))

        season = 0.015 * math.sin(2 * math.pi * (month - 3) / 12.0)
        fx_effect = -0.12 * ((fx - 5.2) / 5.2)  # stronger BRL -> lower basis in USD

        target_usd = ice + 0.03 + season + fx_effect
        cepea_brl = target_usd * fx * (1.0 + 0.01 * math.sin(i / 9.0))

        rows.append(DailyRow(ts=i, month=month, ice_usd_lb=ice, cepea_brl_lp=cepea_brl, fx_usdbrl=fx))

    return rows


def zfx(fx: float, fx_ref: float) -> float:
    return (fx - fx_ref) / fx_ref


def predict_basis(row: DailyRow, p: BasisParams) -> float:
    season = p.month_effects[row.month - 1]
    b = p.beta0 + p.beta1 * zfx(row.fx_usdbrl, p.fx_ref) + season
    return max(-p.max_abs_basis, min(p.max_abs_basis, b))


def predict_mark(row: DailyRow, p: BasisParams) -> float:
    return row.ice_usd_lb + predict_basis(row, p)


def fit_naive(rows: List[DailyRow]) -> BasisParams:
    """Simple moment-fit placeholder; replace with OLS on real history."""
    fx_ref = sum(r.fx_usdbrl for r in rows) / len(rows)
    bases = [r.basis_obs for r in rows]
    beta0 = sum(bases) / len(bases)

    num = 0.0
    den = 0.0
    for r in rows:
        x = zfx(r.fx_usdbrl, fx_ref)
        y = r.basis_obs - beta0
        num += x * y
        den += x * x
    beta1 = num / den if den else 0.0

    month_effects = [0.0] * 12
    counts = [0] * 12
    for r in rows:
        resid = r.basis_obs - beta0 - beta1 * zfx(r.fx_usdbrl, fx_ref)
        month_effects[r.month - 1] += resid
        counts[r.month - 1] += 1
    month_effects = [
        (month_effects[i] / counts[i] if counts[i] else 0.0) for i in range(12)
    ]

    return BasisParams(beta0=beta0, beta1=beta1, month_effects=month_effects, fx_ref=fx_ref)


def evaluate(rows: List[DailyRow], p: BasisParams) -> Tuple[float, float]:
    errs = [abs(predict_basis(r, p) - r.basis_obs) for r in rows]
    mae = sum(errs) / len(errs)
    rmse = math.sqrt(sum(e * e for e in errs) / len(errs))
    return mae, rmse


def main() -> None:
    rows = generate_demo_series()
    split = int(len(rows) * 0.7)
    train, test = rows[:split], rows[split:]

    params = fit_naive(train)
    mae_train, rmse_train = evaluate(train, params)
    mae_test, rmse_test = evaluate(test, params)

    print("Brazil ICE + FX basis model (TEST scaffold)")
    print("=" * 52)
    print(f"fx_ref      = {params.fx_ref:.4f}")
    print(f"beta0       = {params.beta0:.6f} USD/lb")
    print(f"beta1       = {params.beta1:.6f} USD/lb per FX z-score")
    print(f"max_abs     = {params.max_abs_basis:.4f} USD/lb")
    print(f"train MAE   = {mae_train:.6f} | RMSE = {rmse_train:.6f}")
    print(f"test  MAE   = {mae_test:.6f} | RMSE = {rmse_test:.6f}")
    print("\nMonth effects (USD/lb):")
    for i, m in enumerate(params.month_effects, start=1):
        print(f"  month {i:02d}: {m:+.5f}")

    sample = test[-1]
    print("\nSample test row:")
    print(f"  ICE         = {sample.ice_usd_lb:.4f}")
    print(f"  FX          = {sample.fx_usdbrl:.4f}")
    print(f"  Basis obs   = {sample.basis_obs:.4f}")
    print(f"  Basis model = {predict_basis(sample, params):.4f}")
    print(f"  Mark model  = {predict_mark(sample, params):.4f}")

    out = Path(__file__).with_name("README.md")
    if not out.exists():
        out.write_text(
            "# Brazil basis analysis\n\n"
            "Run `python3 brazil_basis_model.py`.\n\n"
            "Replace demo data with CEPEA BRL/lb + ICE + USD/BRL CSV inputs.\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
