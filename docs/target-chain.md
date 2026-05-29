# Target Chain — cotton.xyz

## Current status

| Item | Value |
|------|--------|
| **Target chain (selected)** | **Arbitrum** |
| **Live Testnet target** | **Arbitrum Sepolia** |
| **Production target (future)** | **Arbitrum One** |
| **Current environment** | **TEST** — local relayer only (`network: local`) |
| **On-chain deployment** | None yet |

We are **not** on Arbitrum (or any public network) today. Chain selection is decided; deployment waits until Live Testnet go-live.

---

## Why Arbitrum

- EVM-compatible — fits Solidity + Foundry plan
- Lower fees and fast finality vs Ethereum L1
- Strong DeFi ecosystem and tooling
- MetaMask-friendly for future hedger/trader onboarding
- Keeps relayer/pricing engine chain-agnostic while contracts live on Arbitrum

**Not pursuing for v1:** Sui (full stack pivot), Ethereum L1 mainnet (cost/latency), Hyperliquid path (different architecture).

---

## Network reference

| Network | Chain ID | Use |
|---------|----------|-----|
| **Local Anvil** | `31337` (default) | Current TEST / dev |
| **Arbitrum Sepolia** | `421614` | Live Testnet (first public deploy) |
| **Arbitrum One** | `42161` | Mainnet (post-testnet, if approved) |

**Explorers**
- Arbitrum Sepolia: https://sepolia.arbiscan.io
- Arbitrum One: https://arbiscan.io

**RPC** — configure at deploy time (Alchemy, Infura, or public endpoint). Do not commit private RPC keys.

---

## What is running now (TEST)

- Local Python relayer (oracle / mark / order-book fallback)
- Simulated external feed and order book
- Testnet-styled trade UI (trading disabled)
- No smart contracts, no wallet, no chain ID

This stays in TEST until Live Testnet on **Arbitrum Sepolia**.

---

## Before Live Testnet on Arbitrum Sepolia

1. Deploy contracts (Foundry) to Arbitrum Sepolia
2. Configure RPC + chain ID in frontend wallet flow
3. Testnet USDC (mock token or approved test asset)
4. Oracle adapter (ICE + 24/7 fallback relayer publishing to chain)
5. Update trade UI: network badge **Arbitrum Sepolia**, enable wallet connect
6. Verify mark/oracle consumer on-chain matches relayer output

---

## Related docs

- **`docs/project-status.md`** — current MVP status & handoff (start here)
- `docs/phase-1-task-breakdown.md` — build phases
- `docs/cotton-perp-orderbook-ema-spec.md` — 24/7 pricing / relayer logic
- `docs/basis-layer-research.md` — Brazil / Australia / India basis references & data sources
