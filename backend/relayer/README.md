# cotton.xyz relayer reference (MVP)

This is a reference Python implementation of the order-book EMA relayer described in:

- `docs/cotton-perp-orderbook-ema-spec.md`

It is intentionally small and deterministic for fast iteration.

## Included

- continuous-time EMA oracle fallback
- IPD (impact price difference) from order book depth
- median-of-3 mark price
- bps clamp for oracle/mark
- simple simulator loop for local testing

## Run

```bash
cd backend/relayer
python3 simulator.py
```

The simulator prints JSON lines of relayer updates.

## Next integration steps

1. Replace `fake_external_price()` with real external source adapters.
2. Replace generated order book with live matching engine snapshots.
3. Publish outputs to Redis / WebSocket / DB.
4. Add replay fixtures and unit tests for risk scenarios.
