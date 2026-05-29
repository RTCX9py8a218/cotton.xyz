from dataclasses import dataclass


@dataclass(frozen=True)
class RelayerConfig:
    # EMA decay constants in seconds
    tau_oracle: float = 30.0
    tau_mark: float = 150.0

    # Clamp per tick (50 bps = 0.5%)
    clamp_bps: float = 50.0

    # Impact notional depth in quote terms (USDC)
    impact_notional_q: float = 25_000.0

    # Sanity controls
    max_stale_external_s: float = 5.0
