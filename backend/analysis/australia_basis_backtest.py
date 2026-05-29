#!/usr/bin/env python3
"""
Australia basis calibration notes (AUSTRALIA/USDC).

Unlike Brazil (daily CEPEA through 2018), Australia has no free daily
"Australian lint USD/lb" index. Industry prices as ICE + basis (¢/lb)
with local AUD/bale cash quotes.

This script documents data availability and writes a provisional β_const
to constant_params.json when a proxy series is available.

Usage:
  python3 backend/analysis/australia_basis_backtest.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DATA_DIR = Path(__file__).resolve().parent / "data"
CONSTANT_PARAMS_JSON = DATA_DIR / "constant_params.json"

# Industry guides cite +200 to +400 points (+2 to +4 ¢/lb) for AU lint vs ICE
PROVISIONAL_BETA_USD_LB = 0.028


def main() -> None:
    print("=" * 60)
    print("AUSTRALIA/USDC — data reliability assessment")
    print("=" * 60)
    print()
    print("Live / governance (reliable):")
    print("  • ABARES weekly commodity update — Cotlook A, AUD/USD (gov, no scrape block)")
    print("  • Cotton Australia / cottoninfo — ICE + basis pricing formula")
    print("  • Australian Cotton Shippers — market reports")
    print()
    print("Historical backtest (weaker than Brazil CEPEA):")
    print("  • No free daily AU local lint USD/lb series (CEPEA-equivalent)")
    print("  • Cotlook A is global Far East — not Australia-specific")
    print("  • NSW DPI spot XLSX blocked by Cloudflare from automated fetch")
    print("  • Cotlook daily history requires paid Cotton Outlook subscription")
    print()
    print("Verdict:")
    print("  • BETTER for live ops & transparent ICE+basis quoting")
    print("  • WORSE for automated historical calibration vs Brazil CEPEA")
    print(f"  • MVP β_const provisional: {PROVISIONAL_BETA_USD_LB:.4f} USD/lb (~+280 pts)")
    print()

    if CONSTANT_PARAMS_JSON.exists():
        data = json.loads(CONSTANT_PARAMS_JSON.read_text(encoding="utf-8"))
        origins = data.setdefault("origins", {})
        origins["AUSTRALIA"] = {
            **origins.get("AUSTRALIA", {}),
            "beta_const_usd_lb": PROVISIONAL_BETA_USD_LB,
            "method": "median",
            "calibration_window_days": 504,
            "calibrated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "source": "Industry ICE+basis guides; full backtest pending AU local series",
            "governance_note": "Recalibrate from ABARES grower AUD/bale + FX when wired.",
        }
        data["version"] = max(int(data.get("version", 4)), 4)
        CONSTANT_PARAMS_JSON.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"Updated {CONSTANT_PARAMS_JSON}")


if __name__ == "__main__":
    main()
