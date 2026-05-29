# Brazil Origin Pricing — ICE Anchor + FX-Linked Basis Model

**Goal:** Price Brazil cotton exposure using a **single ICE-anchored perp**, where Brazil-specific adjustment is computed from a **deterministic basis pattern** (especially **USD/BRL**), instead of launching a separate `BRAZIL-BASIS` market.

**Verdict:** **Yes, this is feasible** — and aligns with how Brazilian cotton is already priced in practice (export parity + CEPEA index in BRL).

---

## 1) Why this approach makes sense

Brazilian lint is not priced in isolation. Market participants already think in:

```text
Domestic BRL price  ↔  (ICE USD/lb + export adjustments) × FX − local costs
```

Cepea explicitly compares:
- **CEPEA/ESALQ** (BRL/lb, domestic spot)
- **Export parity** vs ICE
- **USD/lb** equivalents vs ICE first position

So instead of a second perp, we can define:

```text
P_brazil_fair_usd_lb = P_ice_usd_lb + Basis_model(FX, season, params)
```

The smart contract stays **ICE-anchored**; Brazil hedgers get origin-adjusted marks via the basis function.

---

## 2) Core identities

### A) Implied USD price from CEPEA (sanity check feed)

```text
P_cepea_usd_lb = P_cepea_brl_lp / FX_usdbrl
```

### B) Observed basis (what we want to model)

```text
Basis_obs = P_cepea_usd_lb − P_ice_usd_lb
```

### C) Export parity (conceptual, ag-commodity standard in Brazil)

```text
P_fob_usd_lb = P_ice_usd_lb + PortBasis_usd_lb
P_domestic_brl_lp ≈ (P_fob_usd_lb × FX_usdbrl) − LogisticsBRL − TaxesBRL
```

Rearranged to USD/lb:

```text
P_domestic_usd_lb ≈ P_ice_usd_lb + PortBasis_usd_lb − (Logistics + Taxes)/FX
```

**Key insight:** FX enters **inversely** on cost conversion. When BRL weakens (FX ↑), export competitiveness rises, but domestic USD-equivalent pricing dynamics shift — this is the pattern to model.

---

## 3) Empirical pattern (Brazil-specific)

Public research and market structure support:

| Finding | Implication for model |
|--------|------------------------|
| IADB: **negative correlation** between BRL and ag/commodity indexes | Basis moves with FX; not independent |
| Cepea tracks **export parity vs domestic** continuously | Basis is partly structural, partly FX-driven |
| Brazil export share rising; domestic vs export spread varies | Need seasonal + regime terms, not FX alone |
| ICE is USD; CEPEA is BRL | **FX is primary co-variable** for basis vs ICE |

Example (Cepea, May 2026 partial):
- Domestic spot: **R$ 4.2154/lb**
- Export avg: **R$ 3.4776/lb**
- Spread shows domestic premium; USD export ~**$0.70/lb** vs higher implied domestic USD depending on FX

---

## 4) Proposed basis model (v1)

Use a **transparent, calibratable** function (not a black box):

```text
Basis_t = β0
        + β1 · z(FX_t)
        + β2 · Seasonality(month_t)
        + β3 · z(FX_t) · Seasonality(month_t)
```

Where:
- `z(FX_t) = (FX_t − FX_ref) / FX_ref` (FX deviation from trailing reference)
- `Seasonality(m)` = month fixed effects (harvest/export window: Aug–Jul crop year)
- `β` coefficients stored on-chain (governance-updatable) or in immutable params for MVP

### Brazil fair mark (USD/lb)

```text
P_mark_brazil = P_ice + clamp(Basis_t, −B_max, +B_max)
```

### For a single ICE-anchored perp with origin flag

Users choose exposure type:
- **Index (ICE)** mark = `P_ice`
- **Brazil origin-adjusted** mark = `P_mark_brazil`

Same contract, same collateral — different mark function selected by market/oracle route.

---

## 5) Smart contract design (Arbitrum)

### On-chain inputs (oracles)
| Feed | Source | Notes |
|------|--------|-------|
| `P_ice` | Relayer / custom oracle | Already in MVP relayer |
| `FX_usdbrl` | Chainlink BRL/USD on Arbitrum | Widely available |
| `params` | Governance/storage | β0, β1, β2, β3, FX_ref, clamps |

### On-chain computation (Solidity sketch)

```solidity
function brazilBasisUsdLb(
    int256 fx,          // 1e8
    int256 fxRef,       // 1e8
    uint8 month,
    BasisParams calldata p
) internal pure returns (int256) {
    int256 zFx = ((fx - fxRef) * 1e18) / fxRef;
    int256 season = p.monthCoeff[month]; // 1e8
    int256 basis = p.beta0
        + (p.beta1 * zFx) / 1e18
        + season
        + (p.beta2 * zFx * season) / (1e18 * 1e8);
    return clamp(basis, -p.maxAbsBasis, p.maxAbsBasis);
}

function originMarkUsdLb(
    int256 ice,
    int256 fx,
    uint8 month,
    BasisParams calldata p
) external pure returns (int256) {
    return ice + brazilBasisUsdLp(fx, p.fxRef, month, p);
}
```

### What stays off-chain (relayer)
- CEPEA observed series download
- Regression recalibration of `β` coefficients (monthly/quarterly)
- Model error monitoring vs `Basis_obs`
- 24/7 fallback mark logic (order-book EMA) when ICE stale

**Do not** run full regression on-chain — store **coefficients + clamps** on-chain, calibrate off-chain.

---

## 6) Validation framework (deep dive process)

### Step 1 — Build historical dataset
Pull (daily/weekly):
- ICE Cotton No. 2 (USD/lb)
- CEPEA lint (BRL/lb)
- USD/BRL (PTAX or Chainlink-compatible)
- Optional: Cepea export parity USD/lb if available

Compute:
```text
Basis_obs = (CEPEA_BRL / FX) − ICE
```

### Step 2 — Exploratory analysis
- Plot `Basis_obs` vs `FX`
- Plot by month (seasonality)
- Rolling correlation: `corr(Basis_obs, FX)`, `corr(Basis_obs, ΔFX)`
- Regime splits: strong BRL vs weak BRL years

### Step 3 — Fit model v1
- OLS/regularized regression for β coefficients
- Walk-forward backtest (no lookahead)
- Metrics: MAE, RMSE, % within ±X cents/lb, max error during shocks

### Step 4 — Accept/reject criteria
Proceed to on-chain params only if:
- Out-of-sample MAE below threshold (e.g. < 1.5–2.0 ¢/lb for MVP)
- Stable sign on `β1` (FX term) across most rolling windows
- Error spikes flagged → fallback to observed CEPEA override

### Step 5 — Production oracle policy (hybrid)

```text
if CEPEA fresh (<24h):
    Basis = blend(0.7 · Basis_model, 0.3 · Basis_obs)
else:
    Basis = Basis_model(FX, season)
Mark = ICE + Basis
```

This gives reliability + 24/7 continuity.

---

## 7) Why NOT a separate Brazil basis perp (for now)

| Separate basis perp | FX-linked pattern in ICE-anchored contract |
|--------------------|---------------------------------------------|
| More markets to bootstrap | One liquidity pool |
| Speculative distortion in thin basis market | Basis tied to economic parity |
| Harder hedger UX | Hedger selects origin-adjusted mark |
| More oracle attack surface | Fewer primary marks |

You can always add a basis perp later if the modeled spread becomes its own tradable risk factor.

---

## 8) Risks & mitigations

| Risk | Mitigation |
|------|------------|
| FX pattern breaks in crisis | Clamp basis; governance param update; CEPEA override |
| CEPEA stale overnight/weekend | FX+season model fallback |
| Policy/shock (China demand, crop failure) | Residual monitor; widen margin; reduce-only mode |
| Unit/grade mismatch | Fix lint grade assumptions in docs + oracle |
| Overfitting FX | Walk-forward validation; limit parameter count |

---

## 9) MVP recommendation

### Phase 1 (TEST — now)
- Build `backend/analysis/brazil_basis_model.py`
- Ingest historical ICE + FX + synthetic/mock CEPEA until licensed pull
- Output β coefficients + error report

### Phase 2 (TEST)
- Relayer publishes:
  - `ice`
  - `fx_usdbrl`
  - `basis_model`
  - `basis_obs` (when available)
  - `mark_brazil_origin`

### Phase 3 (Arbitrum Sepolia)
- Contract stores `BasisParams`
- Mark function = ICE + `brazilBasis(FX, month)`
- Governance updates coefficients monthly from off-chain calibration

---

## 10) Data sources for calibration

| Data | Provider |
|------|----------|
| CEPEA lint BRL/lb | https://cepea.org.br |
| ICE Cotton No. 2 | ICE / data vendor |
| USD/BRL | BCB PTAX / Chainlink |
| Export parity commentary | Cepea reports |
| Validation | USDA FAS Brazil cotton chapter |

---

## 11) Answer to your question

> Can we define the pattern in the smart contract for pricing anchored to ICE, instead of a separate basis perp?

**Yes.**

Best architecture:
1. **Anchor everything to ICE**
2. Compute **Brazil adjustment** as `Basis(FX, season, params)`
3. Store **params on-chain**, calibrate **off-chain**
4. Use **hybrid oracle** (model + CEPEA observed when fresh)
5. Keep **24/7 fallback** from existing relayer EMA logic

This is technically sound, economically aligned with Brazilian export parity, and simpler to launch than multiple basis markets.

---

## Next implementation step

Run historical calibration script and produce:
- proposed `β0..β3`
- FX sensitivity chart
- seasonality chart
- recommended on-chain clamps (`maxAbsBasis`)

See: `backend/analysis/brazil_basis_model.py`
