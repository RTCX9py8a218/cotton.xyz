import json
import random
import time
from dataclasses import asdict

try:
    from .config import RelayerConfig
    from .engine import update_relayer
    from .models import RelayerState
    from .sim_feed import fake_external_price, make_book
except ImportError:
    from config import RelayerConfig
    from engine import update_relayer
    from models import RelayerState
    from sim_feed import fake_external_price, make_book


def main() -> None:
    cfg = RelayerConfig()
    now = time.time()
    state = RelayerState(ts=now, oracle=78.40, mark=78.40, basis_ema=0.0)

    print("# starting relayer simulator")
    for _ in range(120):
        now = time.time()
        # Slow random walk for internal fair value.
        drift = random.uniform(-0.05, 0.05)
        mid = state.mark + drift
        book = make_book(mid=max(1.0, mid))
        ext = fake_external_price(now, base=mid)

        out = update_relayer(cfg, state, now, book, ext)
        print(json.dumps(asdict(out), separators=(",", ":")))

        state = RelayerState(
            ts=out.ts,
            oracle=out.oracle,
            mark=out.mark,
            basis_ema=out.c2 - out.c1,
        )
        time.sleep(1.0)


if __name__ == "__main__":
    main()
