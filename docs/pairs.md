# Trading pairs (simplified origin notation)

## Overview

| Pair | Meaning | Mark source |
|------|---------|-------------|
| **US/USDC** | US ICE Cotton No. 2 index perp | ICE oracle + US book EMA |
| **BRAZIL/USDC** | Brazil structural + discovered basis perp | ICE + β_const + **Brazil book EMA** |
| **AUSTRALIA/USDC** | Australia structural + discovered basis perp | ICE + β_const + **Australia book EMA** |

All pairs share USDC collateral. **Separate order books** per pair.

---

## US/USDC

- **Anchor:** ICE Cotton No. 2 (USD/lb)
- **Mark:** `median(C1, C2, C3)` on US book
- **Off-hours:** US EMA + internal fallback when external ICE stale

---

## BRAZIL/USDC (v4)

Structural anchor from history; **residual basis from Brazil book EMA**.

```text
C1 = ICE_oracle + β_const           ← governance structural premium
C2 = C1 + EMA(book_mid − C1)        ← Brazil-specific book discovery
C3 = median(bid, ask, last)         ← Brazil book

Mark_Brazil = median(C1, C2, C3)    [clamped per tick]
```

| Component | Source | Updates |
|-----------|--------|---------|
| **β_const** | 504d median CEPEA−ICE | Quarterly governance |
| **Basis EMA** | Brazil order book vs anchor | Continuous (τ≈150s) |
| **Trader residual** | Bids/asks around anchor | Real-time (live testnet) |

### Why separate Brazil EMA?

US EMA only tracks ICE leg. Brazil hedgers need mark to follow **Brazil basis**, not just ICE + fixed wedge. Off-hours / no CEPEA, Brazil EMA keeps mark aligned with where **BRAZIL/USDC** trades.

### Product positioning

- **Not** a tick-for-tick CEPEA replica (Phase 2: CEPEA snap when fresh)
- **Is** a tradable Brazil cotton perp with structural anchor + market-discovered residual
- Hedgers: partial hedge via ICE correlation + on-book Brazil basis

---

## AUSTRALIA/USDC (v4)

Same engine as Brazil; smaller structural β (~+2–4¢/lb vs ICE in industry guides).

```text
C1 = ICE_oracle + β_const           ← governance (industry ICE+basis median)
C2 = C1 + EMA(book_mid − C1)        ← Australia book discovery
C3 = median(bid, ask, last)
Mark_Australia = median(C1, C2, C3)
```

| Component | Source | Updates |
|-----------|--------|---------|
| **β_const** | Industry basis guides / ABARES AUD/bale (pending) | Quarterly governance |
| **Basis EMA** | Australia order book vs anchor | Continuous (τ≈150s) |

### Data note

Australia has **more reliable live references** (ABARES weekly, clear ICE+basis formula) but **no free daily local lint index** like CEPEA for backtest. Product positioning matches Brazil: structural anchor + on-book residual — not a tick-for-tick ABARES replica.

---

## API payload (origin pairs)

```json
{
  "pairs": {
    "BRAZIL/USDC": {
      "mark": 0.87,
      "oracle": 0.87,
      "c1": 0.87,
      "c2": 0.875,
      "c3": 0.874,
      "basis_structural": 0.09,
      "basis_ema": 0.005,
      "basis_traded": 0.004,
      "basis_total": 0.095,
      "mark_model": "ICE + β + Brazil EMA",
      "bids": [...],
      "asks": [...]
    }
  }
}
```

---

## Smart contract (future — Arbitrum)

- `basisConst` on-chain (governance)
- Mark function mirrors C1/C2/C3 with Brazil book feed or relayer attestation
