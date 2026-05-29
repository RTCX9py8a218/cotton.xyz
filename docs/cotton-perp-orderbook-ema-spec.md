# cotton.xyz: Order-Book EMA Spec for 24/7 Cotton Perps

## 1) Objective

Define a production-ready pricing and risk framework for `cotton / USDC` perpetuals that remains robust when external cotton markets are closed.

Design goals:
- 24/7 tradability
- Manipulation resistance
- Smooth but responsive pricing
- Deterministic, auditable relayer behavior

---

## 2) Price Layers

- **External Fair Price (`F_t`)**  
  Derived from ICE Cotton No.2 (plus normalization rules).

- **Oracle Price (`S_t`)**  
  Funding reference and mark input.

- **Mark Price (`M_t`)**  
  Used for margin checks, liquidations, stop/trigger logic, and unrealized PnL.

---

## 3) Operating Modes

### Mode A: External Available
- Set oracle directly from external fair price:
  - `S_t = F_t`
- Internal EMA state remains active but does not override external.

### Mode B: External Unavailable (24/7 fallback)
- Advance oracle using order-book pressure via continuous-time EMA:
  - `S_t = beta * S_(t-) + (1 - beta) * x_t`
  - `beta = exp(-dt / tau_oracle)`
  - `x_t = S_(t-) + IPD_t`

`dt` is elapsed seconds since last relayer update.

---

## 4) Order-Book Pressure (IPD)

Use impact prices at fixed notional depth `Q`:
- `P_impactBid(Q)`: VWAP received when selling notional `Q` into bids
- `P_impactAsk(Q)`: VWAP paid when buying notional `Q` from asks

Let `S` be current oracle (`S_(t-)`). Then:

- `IPD_t = max(P_impactBid - S, 0) - max(S - P_impactAsk, 0)`

Interpretation:
- Positive IPD => upward pressure
- Negative IPD => downward pressure

---

## 5) Mark Price Construction

At each relayer update compute 3 components:

1. `C1 = S_t`  
2. `C2 = S_t + EMA_150(mid_t - S_t)`  
   - `mid_t = (bestBid + bestAsk)/2`
   - EMA uses continuous-time decay with `tau_mark = 150s`
3. `C3 = median(bestBid, bestAsk, lastTrade)`

Final mark:
- `M_raw = median(C1, C2, C3)`

Apply per-update clamp:
- `M_t = clamp(M_raw, M_(t-) * (1 - k), M_(t-) * (1 + k))`
- Suggested `k = 0.005` (±50 bps)

Also clamp oracle similarly:
- `S_t = clamp(S_t, S_(t-) * (1 - k), S_(t-) * (1 + k))`

---

## 6) Funding Input

Funding should reference oracle/mark basis, not last trade:
- `premium_t = (M_t - S_t) / S_t`
- Funding accumulator updates periodically (e.g., hourly) from TWAP of `premium_t`.

---

## 7) Risk Engine Hooks

- **Initial Margin / Maintenance Margin** use `M_t`.
- **Liquidation checks** triggered from `M_t`, never last trade.
- **ADL / backstop logic** keyed to insurance capacity and account health.
- **Stop/trigger execution** should use mark to avoid wick attacks.

---

## 8) Parameter Set (MVP Defaults)

- `tau_oracle = 30s` (fallback oracle responsiveness)
- `tau_mark = 150s` (mark smoothing)
- `k = 0.005` (50 bps per relayer tick clamp)
- `Q` impact depth notional:
  - Stage 1: static (e.g., `Q = 25,000 USDC`)
  - Stage 2: dynamic by observed liquidity/volatility
- Relayer cadence:
  - target: every `1-2s`
  - max stale tolerance: `<= 5s`

---

## 9) Data Quality and Fail-Safes

- Reject external ticks that are stale beyond threshold.
- Reject external jumps beyond sanity envelope unless confirmed by multiple sources.
- If order book depth is insufficient for `Q`, scale `Q` down deterministically and emit flag.
- Emit mode flag on every update: `external` or `internal_fallback`.
- Circuit breaker:
  - if consecutive invalid states exceed threshold, set market to reduce-only.

---

## 10) Relayer Update Pseudocode

```text
onRelayerTick(now):
  dt = now - lastUpdateTs
  betaOracle = exp(-dt / tau_oracle)
  betaMark = exp(-dt / tau_mark)

  book = snapshotOrderBook()
  bestBid, bestAsk, lastTrade = topOfBookAndLastTrade(book)
  mid = (bestBid + bestAsk) / 2

  impactBid = vwapSellAtNotional(book.bids, Q)
  impactAsk = vwapBuyAtNotional(book.asks, Q)
  ipd = max(impactBid - oraclePrev, 0) - max(oraclePrev - impactAsk, 0)

  if externalFairPriceAvailableAndFresh():
      oracleRaw = externalFairPrice()
      mode = "external"
  else:
      x = oraclePrev + ipd
      oracleRaw = betaOracle * oraclePrev + (1 - betaOracle) * x
      mode = "internal_fallback"

  oracle = clampBps(oracleRaw, oraclePrev, 50)

  basis = mid - oracle
  basisEma = betaMark * basisEmaPrev + (1 - betaMark) * basis

  c1 = oracle
  c2 = oracle + basisEma
  c3 = median(bestBid, bestAsk, lastTrade)

  markRaw = median(c1, c2, c3)
  mark = clampBps(markRaw, markPrev, 50)

  publish({
    ts: now, mode, oracle, mark, c1, c2, c3,
    ipd, impactBid, impactAsk, mid, bestBid, bestAsk, lastTrade
  })
```

---

## 11) Telemetry (must-have)

- `mode_external_ratio` (time in external mode)
- `oracle_mark_basis_bps`
- `clamp_hit_rate_oracle`, `clamp_hit_rate_mark`
- `ipd_distribution`
- `depth_coverage_for_Q`
- `stale_tick_count`
- `reduce_only_events`

---

## 12) Implementation Plan (Next Build Step)

1. Build relayer service with deterministic replay.
2. Implement order book impact price functions + tests.
3. Implement oracle fallback and mark median pipeline.
4. Integrate margin/liquidation engine with mark.
5. Add simulations for:
   - external market close
   - shallow book manipulation attempts
   - gap open and volatility shock

