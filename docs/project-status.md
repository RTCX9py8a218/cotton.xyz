# cotton.xyz — Project Status & Handoff

**Last updated:** 27 May 2026  
**Environment:** Local TEST MVP (relayer + UI) → **Arbitrum Sepolia** live testnet (next)  
**Purpose:** Single handoff doc for team review and next-session planning.

---

## 1. Executive summary

**cotton.xyz** is a cotton perpetual DEX using **origin / USDC** pairs anchored to **ICE Cotton No. 2**. Structural basis is governance-calibrated (β_const); residual basis is discovered on separate origin order books via book EMA.

**Current state:** Pricing spine and trade UI shell are in place locally. Three pairs stream live marks over WebSocket. No smart contracts, wallet, or on-chain deployment yet.

**Verdict:** On the **right track** for live testnet MVP architecture. Next milestone is **protocol layer** (contracts + wallet + oracle bridge on Arbitrum Sepolia).

**Session decisions (27 May 2026):**
- Added **AUSTRALIA/USDC** alongside BRAZIL/USDC (same v4 mark engine).
- **Australia preferred over India** for next origin at MVP — clearer ICE+basis model, smaller β, better live data access (ABARES); India deferred to Phase 3 (MSP/unit complexity, wide basis, PDF feeds).
- Agreed local TEST MVP is sufficient foundation; **live testnet** is the next major milestone after contracts.

---

## 2. Trading pairs (live in local relayer)

| Pair | Mark model | β_const (USD/lb) | Book | Status |
|------|------------|------------------|------|--------|
| **US/USDC** | ICE oracle + US book EMA | — | Simulated | ✅ Local TEST |
| **BRAZIL/USDC** | ICE + β + Brazil book EMA | **+9.02¢** (504d CEPEA−ICE median) | Simulated | ✅ Local TEST |
| **AUSTRALIA/USDC** | ICE + β + Australia book EMA | **+2.8¢** (industry guides, provisional) | Simulated | ✅ Local TEST |

All pairs share USDC collateral conceptually; **separate order books** per pair in relayer.

### Mark engine (v4 — origin pairs)

```text
C1 = ICE_oracle + β_const
C2 = C1 + EMA(book_mid − C1)     τ_mark ≈ 150s
C3 = median(best_bid, best_ask, last_trade)

Mark = median(C1, C2, C3)        per-tick clamp ~50 bps
```

US/USDC uses the standard relayer stack (C1 = ICE, no β).

---

## 3. What is built

### Frontend
- `index.html` — investor-style landing page
- `app.html` + `app.js` + `app.css` — dark trade terminal
  - Pair selector: US / Brazil / Australia
  - Candlesticks, EMA 9/21, order book, mark/oracle ticker
  - Origin-only fields: ICE anchor, structural basis, basis EMA, FX (USD/BRL or AUD/USD)
  - Wallet button **disabled**; testnet banner

### Backend
- `backend/api/main.py` — FastAPI (`/health`, `/api/pairs`, `/api/market/latest`, `WS /ws/market`)
- `backend/api/relayer_service.py` — 1s tick, triple-pair payload
- `backend/relayer/` — mark engine, pairs, sim feed, origin constants
- `backend/analysis/` — Brazil backtest, Australia data assessment, `constant_params.json`

### Research & docs
| Doc | Contents |
|-----|----------|
| `docs/white-paper-notes.md` | Working white paper draft |
| `docs/pairs.md` | Pair specs (US, Brazil, Australia) |
| `docs/basis-layer-research.md` | Brazil / Australia / India basis research |
| `docs/brazil-ice-fx-basis-model.md` | Brazil FX model (rejected as primary) |
| `docs/target-chain.md` | Arbitrum Sepolia target |
| `docs/phase-1-task-breakdown.md` | MVP workstreams A–E |
| `docs/cotton-perp-orderbook-ema-spec.md` | Relayer / EMA spec |
| `docs/brazil-basis-backtest.docx` | Backtest report (generated) |

### Brazil backtest (holdout 2012–2018)
| Model | MAE vs CEPEA | vs ICE-only |
|-------|--------------|-------------|
| ICE-only | 7.46¢/lb | baseline |
| **ICE + rolling 504d β (v3/v4 anchor)** | **5.33¢/lb** | **+28.5% PASS** |
| Hybrid CEPEA + FX (v2) | 2.72¢/lb | +63.5% (Phase 2) |

CEPEA CSV ends **2018-05-08**. Live CEPEA needed for modern Brazil validation.

---

## 4. What is NOT built (live testnet blockers)

| Item | Status |
|------|--------|
| Smart contracts (Solidity / Foundry) | ❌ Not started |
| Arbitrum Sepolia deployment | ❌ |
| Wallet connect (MetaMask) | ❌ |
| Testnet USDC | ❌ |
| Oracle adapter (relayer → on-chain) | ❌ |
| Trading API (open / close / reduce) | ❌ |
| Persistent / real order book | ❌ (simulated random walk) |
| Official ICE settlement feed | ❌ (CT=F proxy / sim) |
| Live CEPEA / ABARES ingestion | ❌ (Phase 2) |

---

## 5. Live testnet readiness

| Area | Readiness | Notes |
|------|-----------|-------|
| Pricing / marks | **~85%** | Architecture done; external feed still simulated |
| Product / docs | **~80%** | Honest positioning documented |
| Backend (market data) | **~60%** | WS/REST yes; trading API no |
| Frontend | **~50%** | Display yes; wallet/trading no |
| On-chain | **~0%** | No contracts in repo |
| **Overall live testnet MVP** | **~40%** | Right foundation; protocol layer is the gap |

### Recommended live testnet path

**Phase A — Sepolia vertical slice**
1. Foundry: market config + positions + margin + basic liquidation
2. Deploy to **Arbitrum Sepolia** (chain ID `421614`)
3. Wallet connect + test USDC
4. Relayer oracle adapter (publish mark/oracle)
5. **US/USDC first** on-chain; enable limited trading

**Phase B — Origin perps on testnet**
6. BRAZIL/USDC + AUSTRALIA/USDC with separate books
7. On-chain β_const per origin
8. Low leverage caps, disclaimers in UI

**Phase C — Hardening**
9. Relayer soak + metrics (mode ratio, clamp hits)
10. Replace ICE proxy before public claims
11. Phase 2: CEPEA hybrid (Brazil), ABARES AUD/bale (Australia)

**Deferred:** India (Phase 3), mainnet, tokenomics audit.

---

## 6. Key file map

```text
cotton-landing/
├── index.html, app.html, app.js, app.css    # Landing + trade UI
├── backend/
│   ├── api/main.py, relayer_service.py      # HTTP + WS
│   ├── relayer/
│   │   ├── engine.py                        # US mark (C1/C2/C3)
│   │   ├── brazil_mark.py                   # Origin mark (shared BR + AU)
│   │   ├── origin_constant.py               # β_const per origin
│   │   ├── pairs.py                         # US, BRAZIL, AUSTRALIA
│   │   └── sim_feed.py                      # Simulated books
│   └── analysis/
│       ├── brazil_basis_backtest.py
│       ├── australia_basis_backtest.py
│       └── data/constant_params.json        # Governance β values
└── docs/                                    # All project documentation
```

---

## 7. Run locally

```bash
# Terminal 1 — relayer API
cd ~/Projects/cotton-landing && npm run api:dev

# Terminal 2 — static UI
npm run preview
# → http://localhost:3000/app.html
```

Select **US/USDC**, **BRAZIL/USDC**, or **AUSTRALIA/USDC** in the header. Marks update every ~1s over WebSocket.

### Regenerate Brazil backtest / params

```bash
cd backend && source .venv/bin/activate
python analysis/brazil_basis_backtest.py
python analysis/australia_basis_backtest.py
```

---

## 8. Product language (use / avoid)

**Say:**
- US/USDC = ICE Cotton No. 2 perpetual (global benchmark)
- BRAZIL/USDC = ICE-anchored Brazil perp with governance β + market-discovered residual basis
- AUSTRALIA/USDC = same pattern; industry ICE + basis quoting

**Do not say (MVP):**
- Tick-for-tick CEPEA or ABARES replication
- Zero basis risk for origin hedgers
- FX model as primary Brazil fair value

---

## 9. Tomorrow — suggested agenda

1. **Confirm live testnet scope** — US-only first vs all three pairs day one?
2. **Contract stack** — Foundry layout, market struct, leverage caps, liquidation policy
3. **Oracle design** — relayer push vs signed attestation vs Chainlink-style adapter
4. **Order book** — minimal CLOB vs simplified matching for testnet
5. **Timeline** — M2 (trade lifecycle) target dates from `docs/phase-1-task-breakdown.md`
6. **Open decisions** (from phase-1 doc):
   - External ICE source for testnet
   - Full close vs partial liquidation
   - Initial max leverage / maintenance margin

---

## 10. Related docs (read order)

1. **This file** — current status
2. `docs/target-chain.md` — Arbitrum Sepolia target
3. `docs/phase-1-task-breakdown.md` — MVP workstreams
4. `docs/pairs.md` — pair specifications
5. `docs/white-paper-notes.md` — narrative for final white paper
6. `docs/basis-layer-research.md` — origin expansion research

---

*Handoff prepared end of session 27 May 2026. Resume with Section 9 agenda.*
