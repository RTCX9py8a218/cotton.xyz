#!/usr/bin/env python3
"""
Backtest v3 — ICE + constant structural basis (BRAZIL/USDC).

Mark = ICE + β_const  (β from trailing historical CEPEA−ICE median)
Residual basis discovery left to the order book / trader positioning.

Usage:
  python3 backend/analysis/brazil_basis_backtest.py
"""

from __future__ import annotations

import io
import json
import math
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import requests
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATA_DIR = Path(__file__).resolve().parent / "data"
CEPEA_CSV = DATA_DIR / "precos_cepea_base.csv"
CEPEA_URL = (
    "https://raw.githubusercontent.com/royopa/cepea_scraper/master/bases/precos_cepea_base.csv"
)
RESULTS_JSON = DATA_DIR / "backtest_results.json"
CONSTANT_PARAMS_JSON = DATA_DIR / "constant_params.json"

CALIBRATION_WINDOW = 504
MIN_TRAIN = 252
HOLDOUT_SPLIT = 0.70

# Acceptable thresholds for v3 (logic vs actual CEPEA mark)
ACCEPT_MAE_BASIS_C = 0.06  # 6¢/lb
ACCEPT_VS_ICE_IMPROVE_PCT = 15.0
ACCEPT_WITHIN_5C_PCT = 45.0


@dataclass
class BacktestMetrics:
    n: int
    mae_basis: float
    rmse_basis: float
    mape_mark_pct: float
    r2_basis: float
    pct_within_1pct: float
    pct_within_2c: float
    pct_within_5c: float
    dir_accuracy_pct: float
    mae_mark: float
    rmse_mark: float
    beta_const_mean: float = 0.0


@dataclass
class AccuracyRating:
    grade: str
    score: float
    summary: str
    vs_ice_only_improvement_pct: float
    acceptable: bool


@dataclass
class AcceptanceVerdict:
    passed: bool
    checks: Dict[str, bool]
    summary: str


def ensure_cepea_csv() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not CEPEA_CSV.exists():
        r = requests.get(CEPEA_URL, timeout=120)
        r.raise_for_status()
        CEPEA_CSV.write_bytes(r.content)
    return CEPEA_CSV


def load_cepea() -> pd.DataFrame:
    raw = pd.read_csv(ensure_cepea_csv(), sep=";")
    alg = raw[raw["no_produto"] == "algodao_8_dias"].copy()
    alg["date"] = pd.to_datetime(alg["dt_referencia"]).dt.normalize()
    alg["cepea_usd_lb"] = alg["vr_dolar"] / 100.0
    return alg[["date", "cepea_usd_lb"]].sort_values("date")


def load_ice(start: str = "2000-01-01") -> pd.DataFrame:
    ct = yf.download("CT=F", start=start, progress=False, auto_adjust=False)
    close = ct["Close"].iloc[:, 0] if isinstance(ct.columns, pd.MultiIndex) else ct["Close"]
    ice = close.to_frame("ice_cents")
    ice.index = pd.to_datetime(ice.index).normalize()
    ice["ice_usd_lb"] = ice["ice_cents"] / 100.0
    return ice.reset_index().rename(columns={"Date": "date"})


def build_panel() -> pd.DataFrame:
    panel = load_cepea().merge(load_ice(), on="date", how="inner")
    panel = panel.dropna()
    panel["basis_obs"] = panel["cepea_usd_lb"] - panel["ice_usd_lb"]
    return panel.sort_values("date").reset_index(drop=True)


def compute_metrics(df: pd.DataFrame, pred_col: str = "basis_pred") -> BacktestMetrics:
    obs = df["basis_obs"].values
    pred = df[pred_col].values
    err = pred - obs
    mae = float(np.abs(err).mean())
    rmse = float(np.sqrt((err**2).mean()))

    mark_obs = df["cepea_usd_lb"].values
    mark_pred = df["ice_usd_lb"].values + pred
    mark_err = mark_pred - mark_obs
    mae_mark = float(np.abs(mark_err).mean())
    rmse_mark = float(np.sqrt((mark_err**2).mean()))
    mape = float((np.abs(mark_err) / np.maximum(np.abs(mark_obs), 1e-6)).mean() * 100)

    ss_res = float(((obs - pred) ** 2).sum())
    ss_tot = float(((obs - obs.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot else 0.0

    abs_mark_err = np.abs(mark_err)
    d_obs = obs[1:] - obs[:-1]
    d_pred = pred[1:] - pred[:-1]
    dir_acc = float(((d_obs * d_pred) > 0).mean() * 100) if len(d_obs) else 0.0

    beta_mean = float(df["beta_const"].mean()) if "beta_const" in df.columns else float(pred.mean())

    return BacktestMetrics(
        n=len(df),
        mae_basis=mae,
        rmse_basis=rmse,
        mape_mark_pct=mape,
        r2_basis=r2,
        pct_within_1pct=float((abs_mark_err / np.maximum(np.abs(mark_obs), 1e-6) <= 0.01).mean() * 100),
        pct_within_2c=float((abs_mark_err <= 0.02).mean() * 100),
        pct_within_5c=float((abs_mark_err <= 0.05).mean() * 100),
        dir_accuracy_pct=dir_acc,
        mae_mark=mae_mark,
        rmse_mark=rmse_mark,
        beta_const_mean=beta_mean,
    )


def rate_accuracy(model: BacktestMetrics, ice_only: BacktestMetrics) -> AccuracyRating:
    ice_mae = ice_only.mae_basis
    improvement = ((ice_mae - model.mae_basis) / ice_mae * 100) if ice_mae else 0.0
    err_score = max(0.0, 100 - model.mae_basis * 1000)
    r2_score = max(0.0, min(100.0, max(0.0, model.r2_basis) * 100))
    beat_score = min(30.0, max(0.0, improvement))
    score = 0.45 * err_score + 0.35 * r2_score + 0.20 * beat_score

    acceptable = (
        model.mae_basis <= ACCEPT_MAE_BASIS_C
        and improvement >= ACCEPT_VS_ICE_IMPROVE_PCT
        and model.pct_within_5c >= ACCEPT_WITHIN_5C_PCT
    )

    if acceptable and model.r2_basis >= 0.0:
        grade, summary = "B", "Acceptable anchor — structural constant beats ICE-only; residual basis for traders."
    elif improvement >= ACCEPT_VS_ICE_IMPROVE_PCT and model.mae_basis <= ACCEPT_MAE_BASIS_C:
        grade, summary = "C", "Acceptable MAE vs ICE — constant anchor viable for testnet with disclosed basis risk."
    elif improvement > 0:
        grade, summary = "D", "Marginal — beats ICE-only slightly; recalibrate constant or widen acceptance band."
    else:
        grade, summary = "F", "Not acceptable — constant anchor does not improve on ICE-only."

    return AccuracyRating(
        grade=grade,
        score=round(score, 1),
        summary=summary,
        vs_ice_only_improvement_pct=round(improvement, 1),
        acceptable=acceptable,
    )


def acceptance_verdict(
    recommended: BacktestMetrics, ice: BacktestMetrics, rating: AccuracyRating
) -> AcceptanceVerdict:
    checks = {
        "mae_basis_le_6c": recommended.mae_basis <= ACCEPT_MAE_BASIS_C,
        "beats_ice_by_15pct": rating.vs_ice_only_improvement_pct >= ACCEPT_VS_ICE_IMPROVE_PCT,
        "within_5c_ge_45pct": recommended.pct_within_5c >= ACCEPT_WITHIN_5C_PCT,
        "r2_better_than_ice": recommended.r2_basis > ice.r2_basis,
    }
    passed = all(checks.values())
    if passed:
        summary = (
            "PASS — ICE + constant is an acceptable testnet anchor vs actual CEPEA. "
            "Traders price residual basis around the structural premium."
        )
    else:
        failed = [k for k, v in checks.items() if not v]
        summary = f"REVIEW — failed checks: {', '.join(failed)}"
    return AcceptanceVerdict(passed=passed, checks=checks, summary=summary)


def rolling_constant_backtest(
    panel: pd.DataFrame,
    window: int = CALIBRATION_WINDOW,
    min_train: int = MIN_TRAIN,
    method: str = "median",
) -> pd.DataFrame:
    agg = np.median if method == "median" else np.mean
    rows = []
    for i in range(min_train, len(panel)):
        start = max(0, i - window)
        hist = panel.iloc[start:i]["basis_obs"].values
        beta = float(agg(hist))
        r = panel.iloc[i]
        rows.append(
            {
                "date": r["date"],
                "basis_obs": r["basis_obs"],
                "basis_pred": beta,
                "beta_const": beta,
                "ice_usd_lb": r["ice_usd_lb"],
                "cepea_usd_lb": r["cepea_usd_lb"],
            }
        )
    return pd.DataFrame(rows)


def static_constant_holdout(panel: pd.DataFrame, split: float = HOLDOUT_SPLIT, method: str = "median") -> pd.DataFrame:
    split_idx = int(len(panel) * split)
    train = panel.iloc[:split_idx]
    agg = np.median if method == "median" else np.mean
    beta = float(agg(train["basis_obs"].values))
    test = panel.iloc[split_idx:].copy()
    test["basis_pred"] = beta
    test["beta_const"] = beta
    return test


def save_constant_params(beta: float, method: str, window: int) -> None:
    CONSTANT_PARAMS_JSON.write_text(
        json.dumps(
            {
                "version": 3,
                "mark_model": "ICE + constant",
                "beta_const_usd_lb": beta,
                "method": method,
                "calibration_window_days": window,
                "calibrated_at": datetime.utcnow().isoformat() + "Z",
                "source": "CEPEA algodao 8d minus ICE CT=F",
                "governance_note": "Recalibrate quarterly; residual basis discovered on-book.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def print_metrics(label: str, m: BacktestMetrics) -> None:
    print(f"\n{label}")
    print(f"  n={m.n}  β≈{m.beta_const_mean*100:.2f}¢  basis MAE={m.mae_basis*100:.2f}¢  RMSE={m.rmse_basis*100:.2f}¢")
    print(f"  mark MAE={m.mae_mark*100:.2f}¢  R²={m.r2_basis:.3f}")
    print(f"  within 1%: {m.pct_within_1pct:.1f}%  ±2¢: {m.pct_within_2c:.1f}%  ±5¢: {m.pct_within_5c:.1f}%")


def main() -> None:
    print("Brazil basis backtest v3 — ICE + constant structural premium")
    print("=" * 62)

    panel = build_panel()
    start, end = panel["date"].min().date(), panel["date"].max().date()
    print(f"Panel: {len(panel)} days ({start} → {end})")
    print(f"Basis obs: mean={panel['basis_obs'].mean()*100:.2f}¢  median={panel['basis_obs'].median()*100:.2f}¢  std={panel['basis_obs'].std()*100:.2f}¢")

    split_idx = int(len(panel) * HOLDOUT_SPLIT)
    test_start = panel.iloc[split_idx]["date"]

    roll = rolling_constant_backtest(panel, window=CALIBRATION_WINDOW, method="median")
    hold_static = static_constant_holdout(panel, method="median")
    hold_static_mean = static_constant_holdout(panel, method="mean")

    m_roll_full = compute_metrics(roll)
    h_roll = compute_metrics(roll[roll["date"] >= test_start])
    h_static = compute_metrics(hold_static)
    h_static_mean = compute_metrics(hold_static_mean)
    h_ice = compute_metrics(hold_static.assign(basis_pred=0.0))

    rating = rate_accuracy(h_roll, h_ice)
    verdict = acceptance_verdict(h_roll, h_ice, rating)

    prod_beta = float(np.median(panel.iloc[-CALIBRATION_WINDOW:]["basis_obs"].values))
    save_constant_params(prod_beta, "median", CALIBRATION_WINDOW)

    print(f"\nHoldout: {test_start.date()} → {end}  (n={h_roll.n})")
    print(f"Production β_const (504d median): {prod_beta*100:.2f}¢/lb")

    print_metrics("ICE-only (basis = 0)", h_ice)
    print_metrics("ICE + static β (train median, holdout)", h_static)
    print_metrics("ICE + static β (train mean, holdout)", h_static_mean)
    print_metrics("ICE + rolling 504d median β (recommended)", h_roll)

    print("\n" + "=" * 62)
    print(f"RATING (rolling constant, holdout): {rating.grade}  score={rating.score}/100")
    print(f"  vs ICE-only: {rating.vs_ice_only_improvement_pct:+.1f}%")
    print(f"  {rating.summary}")
    print(f"\nACCEPTANCE: {'PASS ✓' if verdict.passed else 'REVIEW'}")
    print(f"  {verdict.summary}")
    for k, v in verdict.checks.items():
        print(f"    [{('✓' if v else '✗')}] {k}")

    results = {
        "version": 3,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "recommended_model": "ice_plus_constant_504d_median",
        "mark_formula": "Mark_Brazil = ICE + beta_const",
        "panel": {"start": str(start), "end": str(end), "n": len(panel)},
        "holdout_from": str(test_start.date()),
        "production_beta_const_usd_lb": prod_beta,
        "acceptance_thresholds": {
            "mae_basis_max_usd_lb": ACCEPT_MAE_BASIS_C,
            "vs_ice_improvement_min_pct": ACCEPT_VS_ICE_IMPROVE_PCT,
            "within_5c_min_pct": ACCEPT_WITHIN_5C_PCT,
        },
        "acceptance_verdict": asdict(verdict),
        "models_holdout": {
            "ice_only": asdict(h_ice),
            "static_median_train": asdict(h_static),
            "static_mean_train": asdict(h_static_mean),
            "rolling_504d_median": asdict(h_roll),
        },
        "models_full_sample": {
            "rolling_504d_median": asdict(m_roll_full),
        },
        "rating_recommended": asdict(rating),
        "rating": asdict(rating),
        "test_metrics": asdict(h_roll),
        "baselines": {"ice_only": asdict(h_ice)},
        "params": {"beta_const_usd_lb": prod_beta, "method": "median", "window_days": CALIBRATION_WINDOW},
        "data_sources": {
            "cepea": CEPEA_URL,
            "ice": "Yahoo Finance CT=F",
        },
        "limitations": [
            "Constant captures structural premium only; residual basis (~10¢ vol) is trader-discovered.",
            "CEPEA CSV ends 2018-05-08.",
            "ICE proxy is CT=F front future.",
        ],
    }
    RESULTS_JSON.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved → {RESULTS_JSON}")
    print(f"Relayer params → {CONSTANT_PARAMS_JSON}")


if __name__ == "__main__":
    main()
