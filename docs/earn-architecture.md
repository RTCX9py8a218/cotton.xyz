# Earn — USDC idle yield (architecture)

**Status:** Testnet UI + local demo (Phase 1)  
**Target chain:** Arbitrum Sepolia → Arbitrum One  
**Future lane:** SATA / dividend-backed yield via partner (Phase 3)

---

## Product goal

Let traders earn on **idle USDC** while waiting between cotton perp trades. Margin and order collateral stay liquid in the **Trading** bucket.

---

## Balance buckets

| Bucket | Earns? | Used for |
|--------|--------|----------|
| **Trading** | No | Free collateral, deposits to Earn |
| **In open orders** | No | Reserved limit/stop margin |
| **Posted margin** | No | Open positions (not in demo yet) |
| **Earning (vault)** | Yes | Idle USDC in yield vault |
| **Accrued yield** | — | Claimed to Trading on withdraw |

**Rule:** Only explicit user **Deposit to Earn** moves USDC out of Trading. **Withdraw to Trading** must be instant before order entry (live testnet requirement).

---

## Phase roadmap

### Phase 1 — Now (testnet demo)

- `earn.html` + `earn.js`
- Local state (`localStorage`) — simulated balances
- Mock **4.5% APY** USDC base vault
- Simple time-based accrual on earning balance
- Disclosures + SATA shown as **future** vault track

### Phase 2 — Live testnet (Arbitrum)

- Wallet connect (USDC on Arbitrum Sepolia)
- On-chain vault: **Morpho USDC** or **Aave USDC** (instant withdraw priority)
- Contract adapter: `deposit(tradingAccount, amount)` / `withdraw(tradingAccount, amount)`
- Pre-trade hook: optional auto-withdraw if trading balance &lt; order margin

### Phase 3 — SATA / Strive lane (optional)

- Partner integration (e.g. **Apyx** dividend-backed stablecoin stack referencing **SATA** collateral basket)
- Separate vault product — not commingled with base USDC vault without disclosure
- Legal review: securities marketing, ROC tax treatment, rate variability
- Daily accrual display aligned with SATA dividend frequency when partner API exists

---

## UI surfaces

| Surface | Path |
|---------|------|
| Earn page | `earn.html` |
| Trade (link in nav) | `app.html` |
| Portfolio (future) | aggregated Trading + Earn |

Nav: **Trade · Markets · Earn · Portfolio**

---

## Risk & copy

- Not FDIC insured
- Smart-contract risk when live
- APY variable; testnet APY is illustrative
- SATA track is **not** a direct purchase of listed preferred stock in Phase 1–2
- Earn balance must not delay liquidations — margin stays outside vault

---

## Files

| File | Role |
|------|------|
| `earn.html` | Earn UI |
| `earn.js` | Demo state, accrual, deposit/withdraw |
| `docs/earn-architecture.md` | This document |

---

## Integration checklist (Phase 2)

- [ ] Vault contract address on Arbitrum Sepolia
- [ ] USDC approve + deposit/withdraw from connected wallet
- [ ] Sync Trading balance with on-chain margin account
- [ ] Block Earn deposit if amount &gt; free collateral
- [ ] Metrics: TVL in Earn, avg APY, withdraw latency
- [ ] Legal disclaimer in UI + white paper

---

*Last updated: May 2026*
