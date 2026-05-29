# cotton.xyz DEX: Phase 1 Task Breakdown (MVP)

## Scope (Phase 1)

Deliver a testable `cotton / USDC` perpetual MVP with:
- wallet connect + basic trading UI
- order-book-driven oracle/mark relayer
- core margin/PnL/liquidation checks
- local environment for deterministic testing

Target outcome: one end-to-end vertical slice that can open/close positions and stream mark/oracle updates in real time.

---

## Workstreams

## A) Protocol / Contracts

### A1. Market Config Contract
- Define market ID, collateral asset, leverage bounds, and risk params.
- Expose admin setters for safe parameter updates (guarded).
- Acceptance:
  - can initialize/update market params in local testnet
  - emits events on each parameter update

### A2. Position & Margin Core
- Track positions (side, size, entry, margin, funding accumulator).
- Support open/increase/reduce/close flows.
- Compute unrealized PnL off relayed mark price.
- Acceptance:
  - deterministic PnL for long/short test vectors
  - margin checks block under-collateralized opens

### A3. Liquidation Module (MVP)
- Trigger liquidation when equity < maintenance margin.
- Partial liquidation optional; full close acceptable for MVP.
- Acceptance:
  - liquidation test cases pass for price shocks
  - healthy positions cannot be liquidated

---

## B) Relayer / Pricing Engine

### B1. Order Book Snapshot Interface
- Normalize bids/asks + last trade from local engine.
- Provide impact-VWAP at target notional depth `Q`.
- Acceptance:
  - impact bid/ask deterministic for fixed snapshots
  - handles shallow book by deterministic depth scaling

### B2. Oracle Engine
- External mode: oracle from external fair source.
- Fallback mode: continuous-time EMA with IPD.
- Per-tick clamp (bps) and stale-data checks.
- Acceptance:
  - mode switch external->fallback->external works
  - clamp and stale guards enforced in tests

### B3. Mark Engine
- Compute 3 components and median mark.
- Maintain basis EMA state (`tau_mark`).
- Publish trace fields for auditability.
- Acceptance:
  - mark output deterministic across replay
  - anti-spike behavior validated with adversarial ticks

---

## C) Backend API / Streaming

### C1. Market Data API
- REST: latest oracle, mark, top-of-book, mode flag.
- WS: stream relayer updates at 1-2s cadence.
- Acceptance:
  - UI can subscribe and render live values
  - reconnect behavior tested

### C2. Trading API
- Place market/limit (or simulated fills for MVP).
- Position query endpoint.
- Acceptance:
  - can open/reduce/close via API calls
  - rejected requests return explicit risk reason

---

## D) Frontend (Trading Shell)

### D1. Core Views
- Order book, mark/oracle panel, position table, trade ticket.
- Wallet connect + network status.
- Acceptance:
  - live updates visible from WS stream
  - user can submit and track position lifecycle

### D2. Risk UX
- Show liquidation price and margin ratio before submit.
- Show mode flag (`external` vs `internal_fallback`).
- Acceptance:
  - user sees warning before high-risk leverage action

---

## E) Data / Infra / DevEx

### E1. Local Stack
- Docker compose: backend, relayer, postgres, redis, anvil.
- Seed scripts for mock users + initial order book.
- Acceptance:
  - one command startup
  - health checks green

### E2. Observability
- Structured logs for relayer components (C1/C2/C3, clamp hits, IPD).
- Basic metrics endpoint.
- Acceptance:
  - mode ratio and clamp hit rate visible during soak run

---

## Milestones

### M1 (Week 1): Pricing Spine
- B1+B2+B3 complete
- deterministic replay available

### M2 (Week 2): Trade Lifecycle
- A2+A3+C2 complete
- end-to-end open/close with mark-based checks

### M3 (Week 3): UI + Integration
- D1+D2+C1 complete
- operator can run local demo start-to-finish

### M4 (Week 4): Hardening
- E1+E2 complete
- runbook + regression tests + scenario suite

---

## Blocking Decisions Needed Before Coding

See also: **`docs/target-chain.md`** (Target Chain: **Arbitrum**)

1. **Target chain** — **Arbitrum** (Live Testnet: **Arbitrum Sepolia**; production: **Arbitrum One**). Current build remains local TEST until deploy.
2. Chain/contract framework preference for MVP (Foundry + Solidity assumed).
3. External fair source provider for cotton (single source vs multi-source).
4. Liquidation policy for MVP (full close vs partial).
5. Initial leverage caps and maintenance margin.
6. Target relayer cadence (1s vs 2s).
