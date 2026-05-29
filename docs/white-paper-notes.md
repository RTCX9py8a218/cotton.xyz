# cotton.xyz — White Paper Notes (Working Draft)

**Status:** Internal working notes for final White Paper  
**Environment:** TEST / local relayer MVP → Arbitrum live testnet (planned)  
**Last updated:** 27 May 2026 (see `docs/project-status.md` for handoff)

---

## 1. Executive Summary

**cotton.xyz** is a cotton perpetual DEX designed around simplified **origin / USDC** pairs rather than commodity ticker strings. The protocol anchors global exposure to **ICE Cotton No. 2** and offers **origin-adjusted** markets (**Brazil**, **Australia**) where structural basis is governance-calibrated and **residual basis is discovered by traders** on-book.

Core design principles captured in this document:

1. **ICE as universal anchor** — one global cotton reference (USD/lb).
2. **Origin markets via structural adjustment** — not separate opaque basis perps at launch.
3. **24/7 marks** — relayer with external oracle + order-book EMA fallback.
4. **Honest product positioning** — origin perps (BRAZIL/USDC, AUSTRALIA/USDC) are tradable structural anchors + book discovery, not tick-for-tick local index replicas at MVP.
5. **Arbitrum** as target chain for live testnet and production.

---

## 2. Market Structure

### 2.1 Pair naming

| Pair | Description |
|------|-------------|
| **US/USDC** | ICE Cotton No. 2 index perpetual — global benchmark exposure |
| **BRAZIL/USDC** | ICE anchor + Brazil structural premium + book-discovered residual basis |
| **AUSTRALIA/USDC** | ICE anchor + Australia structural premium + book-discovered residual basis |

All pairs use **USDC collateral** and share relayer infrastructure but maintain **separate order books**.

### 2.2 Target users

| User | US/USDC | BRAZIL/USDC | AUSTRALIA/USDC |
|------|---------|-------------|----------------|
| Global speculators / benchmark hedgers | Primary | Secondary | Secondary |
| Brazil origin hedgers (partial) | — | Phase 1 | — |
| Australia origin hedgers (partial) | — | — | Phase 1 |
| Basis traders | — | Primary | Primary (residual discovery) |
| Full local index replication hedgers | — | Phase 2 (CEPEA) | Phase 2 (ABARES/AUD-bale) |

---

## 3. Mark Engine Architecture (Current — v4)

### 3.1 US/USDC

Standard relayer median mark with three components:

```text
C1 = ICE oracle (external when fresh)
C2 = C1 + EMA(book_mid − C1)        τ_mark ≈ 150s
C3 = median(best_bid, best_ask, last_trade)

Mark_US = median(C1, C2, C3)        [per-tick clamp ~50 bps]
```

**Off-hours / stale external feed:** internal fallback via IPD + continuous-time EMA on order-book basis.

### 3.2 BRAZIL/USDC

Separate Brazil relayer leg with **its own order book and EMA state**:

```text
C1_br = ICE_oracle + β_const
C2_br = C1_br + EMA(Brazil_book_mid − C1_br)
C3_br = median(best_bid, best_ask, last_trade)   [Brazil book]

Mark_Brazil = median(C1_br, C2_br, C3_br)       [per-tick clamp]
```

| Component | Role | Update frequency |
|-----------|------|------------------|
| **β_const** | Governance structural premium (historical CEPEA−ICE) | Quarterly recalibration |
| **Basis EMA** | Book-discovered residual basis | Continuous (~150s decay) |
| **Brazil book** | Trader long/short expression of premium/discount | Real-time (live testnet) |

**Why separate Brazil EMA (key design decision):**

- US EMA only tracks the **ICE leg** — it does not capture Brazil-specific basis dynamics.
- A fixed β_const from 504-day history captures **long-run** Brazil premium but not **current** market views or regime shifts.
- Without Brazil-specific EMA, off-hours marks drift with ICE alone → **unreliable for hedgers**.
- Residual basis (~10¢/lb historical vol) is ** intentionally left to traders**, not modeled by FX formulas.

### 3.3 AUSTRALIA/USDC

Same v4 stack as Brazil — separate order book and EMA state:

```text
C1_au = ICE_oracle + β_const_au
C2_au = C1_au + EMA(Australia_book_mid − C1_au)
C3_au = median(best_bid, best_ask, last_trade)   [Australia book]

Mark_Australia = median(C1_au, C2_au, C3_au)
```

| Component | Role | Update frequency |
|-----------|------|------------------|
| **β_const_au** | Governance structural premium (industry ICE+basis guides) | Quarterly recalibration |
| **Basis EMA** | Book-discovered residual basis | Continuous (~150s decay) |
| **Australia book** | Trader expression of premium/discount | Real-time (live testnet) |

**Australia-specific notes:**

- Industry quotes lint as **ICE + basis (points)** — same mental model as the mark engine.
- Structural β is **smaller** than Brazil (~+2.8¢/lb provisional vs ~+9¢/lb CEPEA median).
- Live governance path: **ABARES weekly** (Cotlook A, AUD/USD) + merchant basis reports.
- No free daily AU-local lint index for historical backtest (unlike CEPEA through 2018).

### 3.4 β_const calibration

```text
β_const = median(Basis_obs) over trailing 504 trading sessions
Basis_obs = CEPEA_USD/lb − ICE_USD/lb
```

- **Source (research):** CEPEA algodão 8 dias, ICE CT=F proxy, FRED USD/BRL (historical panel 2000–2018).
- **Production value (last calibration):** ~+9.02¢/lb (504d median through May 2018).
- **Australia (provisional):** ~+2.8¢/lb from industry ICE+basis guides; pending ABARES AUD/bale series.
- **Governance:** quarterly update; stored on-chain as fixed-point scalar (future).
- **Not clamped** in relayer — governance sets the exact value.

---

## 4. Architecture Evolution (Decision Log)

### v1 — Static FX + season model (rejected as primary)

```text
Basis = β₀ + β₁·z(FX) + seasonality(month)
Mark  = ICE + Basis
```

**Backtest result (holdout 2012–2018):** MAE **7.70¢/lb** — **worse than ICE-only** (7.46¢).  
**Verdict:** FX explains weak correlation (~−0.13 to −0.29) with Brazil basis. Not suitable as primary mark engine.

### v2 — Hybrid oracle (CEPEA lag + rolling FX fallback)

**Backtest result:** MAE **2.72¢/lb** (+63.5% vs ICE-only).  
**Verdict:** Good for **hedger-grade accuracy** when CEPEA is available; requires live CEPEA feed. Deferred as Phase 2 overlay.

### v3 — ICE + constant structural premium

```text
Mark_Brazil = ICE + β_const
```

**Backtest result:** MAE **5.33¢/lb** rolling 504d median (+28.5% vs ICE-only). **Acceptance: PASS** for testnet anchor.  
**Limitation:** No Brazil-specific book feedback; US EMA only.

### v4 — ICE + β_const + Brazil book EMA (current)

**Rationale (user insight):** β_const from 504d history largely pre-empts what traders would discover; without Brazil EMA the gap vs actual CEPEA widens off-hours → poor hedge reliability.

**Implementation:** Separate Brazil C1/C2/C3 stack, separate order book, trader residual discovery on-book.

---

## 5. Backtest Summary (Logic vs Actual CEPEA)

**Data:** CEPEA algodão 8d (royopa CSV, 2000–2018), ICE CT=F, 4,440 aligned days.  
**Holdout:** Nov 2012 – May 2018 (30% of sample).

| Model | Holdout MAE (mark) | vs ICE-only | Within ±5¢ |
|-------|-------------------|-------------|------------|
| ICE-only | 7.46¢/lb | baseline | 35.6% |
| ICE + static β (train mean) | 5.61¢/lb | +24.8% | 48.5% |
| **ICE + rolling 504d median β** | **5.33¢/lb** | **+28.5%** | **52.7%** |
| FX + season (v1) | 7.70¢/lb | −3.1% | 35.1% |
| Hybrid CEPEA + FX (v2) | 2.72¢/lb | +63.5% | 82.5% |
| CEPEA + ICE bridge (research) | ~0.22¢/lb | — | ~96.8% |

**Acceptance criteria (v3 constant anchor):**

- MAE ≤ 6¢/lb ✓  
- Beat ICE-only by ≥ 15% ✓  
- ≥ 45% of marks within ±5¢ of CEPEA ✓  

**Important caveat:** Historical CEPEA CSV ends **2018-05-08**. Modern validation requires live CEPEA ingestion before live testnet claims.

**Accuracy targets (research — not MVP claims):**

| Approach | ~Within 1% of CEPEA |
|----------|---------------------|
| CEPEA + ICE bridge (same-day + stale bridge) | ~88% holdout |
| Hybrid CEPEA oracle (v2) | ~87% |
| ICE + constant only | ~9% |
| Tick-for-tick CEPEA replica | 100% on publish days only |

**99% accuracy** is achievable only with: (a) CEPEA as primary oracle when fresh, (b) ICE bridge between publishes, (c) official ICE settlement feed — **not** with FX model or fixed constant alone.

---

## 6. 24/7 Relayer Specification

### 6.1 Operating modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| **External** | ICE feed fresh (<5s) | Oracle = external price |
| **Internal fallback** | ICE feed stale | Oracle = EMA(IPD-adjusted prior oracle) |

Brazil leg inherits ICE oracle mode for C1 anchor; origin EMA (Brazil, Australia) provides independent off-hours stabilization.

### 6.2 Key parameters (TEST)

| Parameter | Value |
|-----------|-------|
| τ_oracle | 30s |
| τ_mark | 150s |
| Per-tick clamp | 50 bps |
| Impact notional Q | $25,000 USDC |
| β_const calibration window | 504 sessions |
| CEPEA freshness (future hybrid) | ≤24h |

### 6.3 API surface

- `GET /health`
- `GET /api/market/latest`
- `GET /api/pairs`
- `WS /ws/market` — 1s tick, triple pair payload (US, Brazil, Australia)

---

## 7. Product Positioning (Recommended Language)

### What we say

> **US/USDC** — ICE Cotton No. 2 perpetual. Global cotton benchmark.  
> **BRAZIL/USDC** — ICE-anchored Brazil cotton perpetual with a governance-set structural premium (β_const). Additional Brazil basis is discovered by the market via the order book.

### What we do not say (MVP)

- ❌ “Replicates CEPEA index tick-for-tick”  
- ❌ “Full Brazil origin hedge with zero basis risk”  
- ❌ “FX model predicts Brazil fair value”  

### Phase 2 upgrade path (hedger-grade)

1. Live CEPEA ingestion → snap/override when fresh  
2. ICE bridge between CEPEA publishes (off-hours)  
3. Official ICE settlement index (replace CT=F front-month proxy)  
4. Chainlink BRL/USD on Arbitrum (for hybrid oracle, if needed)  

---

## 8. Smart Contract Notes (Future — Arbitrum)

### 8.1 Chain selection

| Environment | Chain |
|-------------|-------|
| Current TEST | Local relayer |
| Live testnet (planned) | **Arbitrum Sepolia** (421614) |
| Production (planned) | **Arbitrum One** (42161) |

**Rationale:** EVM ecosystem, USDC native, Chainlink feeds, low gas vs Ethereum L1.

### 8.2 On-chain parameters (sketch)

```solidity
struct BrazilMarkParams {
    int256 basisConstUsdLb;     // governance β_const (fixed-point)
    uint256 lastCalibratedAt;
    uint256 calibrationsWindow; // 504
}

// Mark function mirrors off-chain C1/C2/C3 with book attestation or relayer oracle
```

### 8.3 Governance

- **β_const:** quarterly multisig update from off-chain calibration pipeline  
- **Emergency:** basis clamp widening, relayer pause, CEPEA override flag  
- **Transparency:** publish C1/C2/C3 components, β_const, basis EMA on-chain or via attestation  

---

## 9. Risk & Governance Framework (White Paper Section)

| Risk | Mitigation |
|------|------------|
| β_const stale after regime shift | Quarterly recalibration; Brazil EMA allows mark to diverge from anchor |
| ICE proxy ≠ settlement index | Upgrade to official ICE feed before live testnet |
| CEPEA unavailable | Brazil EMA + ICE anchor; disclose wider basis risk |
| Thin Brazil book off-hours | EMA smoothing; minimum spread governance |
| Manipulation (thin book) | Impact notional Q, median mark, per-tick clamps |
| Hedger basis mismatch | Phase 2 CEPEA layer; clear product disclaimers at MVP |

---

## 10. Roadmap Alignment

| Phase | Scope |
|-------|-------|
| **MVP (current)** | Landing page, relayer, trade UI (TEST), US/USDC + BRAZIL/USDC + AUSTRALIA/USDC marks, simulated books |
| **Live testnet** | Arbitrum Sepolia, wallet connect, real origin order books, disabled→enabled trading |
| **Phase 2** | CEPEA hybrid oracle (Brazil), ABARES AUD/bale calibration (Australia), official ICE feed, on-chain β_const |
| **Phase 3** | India origin, basis research per remaining origin |
| **Production** | Arbitrum One, audited contracts, governance tokenomics (see investor deck) |

---

## 11. Key Quotes / Rationale (For White Paper Narrative)

> “We do not launch a separate BRAZIL-BASIS perp. Brazil exposure is ICE-anchored with a transparent structural adjustment and market-discovered residual basis.”

> “A 504-day constant captures the long-run Brazil premium; traders price the marginal basis. The Brazil EMA ensures off-hours marks stay tied to where the perp actually trades.”

> “FX-linked basis models failed out-of-sample. The market is the better oracle for residual basis; governance is the better oracle for structural basis.”

> “99% mark accuracy vs CEPEA requires CEPEA oracle integration — not a fixed constant. Our MVP is honest about that and builds the architecture to get there.”

---

## 12. Technical Artifacts (Reference)

| Artifact | Path |
|----------|------|
| Pair specification | `docs/pairs.md` |
| Brazil basis research | `docs/brazil-ice-fx-basis-model.md` |
| Basis layer research | `docs/basis-layer-research.md` |
| Order-book EMA spec | `docs/cotton-perp-orderbook-ema-spec.md` |
| Target chain | `docs/target-chain.md` |
| Backtest report (DOCX) | `docs/brazil-basis-backtest.docx` |
| Backtest JSON | `backend/analysis/data/backtest_results.json` |
| Production β_const | `backend/analysis/data/constant_params.json` |
| Origin mark engine | `backend/relayer/brazil_mark.py` (shared by Brazil + Australia) |
| Origin β loader | `backend/relayer/origin_constant.py` |
| Australia data notes | `backend/analysis/australia_basis_backtest.py` |
| Relayer service | `backend/api/relayer_service.py` |

---

## 13. Open Items for Final White Paper

- [ ] Tokenomics section (from investor deck — `$CTN`, fee splits, governance)
- [ ] Competitive landscape (trade.xyz, TradFi cotton, other perp DEXs)
- [ ] Legal / regulatory framing (commodity perp, offshore, disclaimers)
- [ ] Live testnet launch criteria checklist
- [ ] CEPEA data licensing for production oracle
- [ ] Formal security audit scope (contracts + relayer)
- [ ] Australia / India origin expansion thesis (from basis-layer research)

**Handoff:** See `docs/project-status.md` (27 May 2026) for full status and tomorrow agenda.

---

*These notes synthesize architecture decisions, backtest evidence, and product positioning from the cotton.xyz TEST MVP build. Expand into formal White Paper prose, diagrams, and legal review before public release.*
