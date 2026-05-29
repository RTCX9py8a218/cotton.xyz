import asyncio
import random
import time
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Set

from relayer.brazil_basis import simulate_fx_usdaud, simulate_fx_usdbrl
from relayer.brazil_constant import load_constant_config
from relayer.brazil_mark import BrazilMarkState, update_brazil_mark
from relayer.config import RelayerConfig
from relayer.engine import update_relayer
from relayer.models import RelayerOutput, RelayerState
from relayer.origin_constant import load_origin_config
from relayer.pairs import DEFAULT_PAIR, PAIRS
from relayer.sim_feed import fake_external_price, make_book, make_origin_book


def _book_levels(book) -> Dict[str, Any]:
    return {
        "bids": [{"price": lv.price, "size": lv.size} for lv in book.bids[:14]],
        "asks": [{"price": lv.price, "size": lv.size} for lv in book.asks[:14]],
        "best_bid": book.bids[0].price if book.bids else 0.0,
        "best_ask": book.asks[0].price if book.asks else 0.0,
        "last_trade": book.last_trade,
        "mid": (book.bids[0].price + book.asks[0].price) / 2.0 if book.bids and book.asks else 0.0,
    }


def _origin_pair_payload(
    *,
    pair_id: str,
    levels: Dict[str, Any],
    mark_out,
    mode: str,
    beta_const: float,
    mark_model: str,
    fx_field: Optional[tuple[str, float]] = None,
) -> Dict[str, Any]:
    payload = {
        **levels,
        "pair": pair_id,
        "origin": PAIRS[pair_id]["origin"],
        "anchor": "ICE",
        "mark": mark_out.mark,
        "oracle": mark_out.oracle,
        "mode": mode,
        "ts": mark_out.ts,
        "ice_anchor": mark_out.ice_anchor,
        "c1": mark_out.c1,
        "c2": mark_out.c2,
        "c3": mark_out.c3,
        "basis_structural": mark_out.basis_structural,
        "basis_ema": mark_out.basis_ema,
        "basis_traded": mark_out.basis_traded,
        "basis_total": mark_out.basis_structural + mark_out.basis_ema,
        "impact_bid": mark_out.impact_bid,
        "impact_ask": mark_out.impact_ask,
        "mark_model": mark_model,
        "environment": "testnet",
        "network": "local",
    }
    if fx_field:
        payload[fx_field[0]] = fx_field[1]
    return payload


class RelayerService:
    def __init__(self, tick_interval_s: float = 1.0) -> None:
        self.cfg = RelayerConfig()
        self.brazil_const = load_constant_config()
        self.australia_const = load_origin_config("AUSTRALIA")
        self.tick_interval_s = tick_interval_s
        now = time.time()
        br_beta = self.brazil_const.beta_const_usd_lb
        au_beta = self.australia_const.beta_const_usd_lb
        self._state = RelayerState(ts=now, oracle=78.40, mark=78.40, basis_ema=0.0)
        self._brazil_state = BrazilMarkState(
            ts=now,
            oracle=78.40 + br_beta,
            mark=78.40 + br_beta,
            basis_ema=0.0,
        )
        self._australia_state = BrazilMarkState(
            ts=now,
            oracle=78.40 + au_beta,
            mark=78.40 + au_beta,
            basis_ema=0.0,
        )
        self._trader_residual: Dict[str, float] = {"BRAZIL": 0.0, "AUSTRALIA": 0.0}
        self._fx_usdbrl = 5.50
        self._fx_usdaud = 0.65
        self._latest: Optional[RelayerOutput] = None
        self._latest_payload: Optional[Dict[str, Any]] = None
        self._subscribers: Set[asyncio.Queue] = set()
        self._task: Optional[asyncio.Task] = None

    @property
    def latest(self) -> Optional[Dict[str, Any]]:
        return self._latest_payload

    async def start(self) -> None:
        if self._task is None:
            await self._tick()
            self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=32)
        self._subscribers.add(queue)
        if self._latest_payload is not None:
            queue.put_nowait(self._latest_payload)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    def _evolve_trader_residual(self, origin: str) -> None:
        """TEST: slow random walk of trader-implied basis on top of structural anchor."""
        prev = self._trader_residual.get(origin, 0.0)
        nxt = prev + random.uniform(-0.002, 0.002)
        self._trader_residual[origin] = max(-0.06, min(0.06, nxt))

    async def _broadcast(self, payload: Dict[str, Any]) -> None:
        dead: List[asyncio.Queue] = []
        for queue in self._subscribers:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    queue.put_nowait(payload)
                except asyncio.QueueFull:
                    dead.append(queue)
        for queue in dead:
            self.unsubscribe(queue)

    async def _run_loop(self) -> None:
        while True:
            await asyncio.sleep(self.tick_interval_s)
            await self._tick()

    def _update_origin_leg(
        self,
        *,
        state: BrazilMarkState,
        now: float,
        ice_oracle: float,
        beta_const: float,
        mode: str,
        origin: str,
    ):
        self._evolve_trader_residual(origin)
        structural_anchor = ice_oracle + beta_const
        book = make_origin_book(
            anchor_mid=structural_anchor,
            trader_residual_basis=self._trader_residual[origin],
        )
        out = update_brazil_mark(
            self.cfg,
            state,
            now,
            book,
            ice_oracle=ice_oracle,
            beta_const=beta_const,
            mode=mode,
        )
        new_state = BrazilMarkState(
            ts=out.ts,
            mark=out.mark,
            oracle=out.oracle,
            basis_ema=out.basis_ema,
        )
        return out, new_state, book

    async def _tick(self) -> None:
        now = time.time()
        br_beta = self.brazil_const.beta_const_usd_lb
        au_beta = self.australia_const.beta_const_usd_lb

        # --- US/USDC leg ---
        us_drift = random.uniform(-0.05, 0.05)
        us_mid = max(1.0, self._state.mark + us_drift)
        us_book = make_book(mid=us_mid)
        ext = fake_external_price(now, base=us_mid)

        out = update_relayer(self.cfg, self._state, now, us_book, ext)
        self._latest = out
        self._state = RelayerState(
            ts=out.ts,
            oracle=out.oracle,
            mark=out.mark,
            basis_ema=out.c2 - out.c1,
        )

        self._fx_usdbrl = simulate_fx_usdbrl(self._fx_usdbrl)
        self._fx_usdaud = simulate_fx_usdaud(self._fx_usdaud)

        br_out, self._brazil_state, br_book = self._update_origin_leg(
            state=self._brazil_state,
            now=now,
            ice_oracle=out.oracle,
            beta_const=br_beta,
            mode=out.mode,
            origin="BRAZIL",
        )
        au_out, self._australia_state, au_book = self._update_origin_leg(
            state=self._australia_state,
            now=now,
            ice_oracle=out.oracle,
            beta_const=au_beta,
            mode=out.mode,
            origin="AUSTRALIA",
        )

        us_levels = _book_levels(us_book)
        br_levels = _book_levels(br_book)
        au_levels = _book_levels(au_book)

        us_pair = {
            **_book_levels(us_book),
            "pair": "US/USDC",
            "origin": PAIRS["US/USDC"]["origin"],
            "anchor": "ICE",
            "mark": out.mark,
            "oracle": out.oracle,
            "mode": out.mode,
            "ts": out.ts,
            "c1": out.c1,
            "c2": out.c2,
            "c3": out.c3,
            "ipd": out.ipd,
            "impact_bid": out.impact_bid,
            "impact_ask": out.impact_ask,
            "environment": "testnet",
            "network": "local",
        }
        br_pair = _origin_pair_payload(
            pair_id="BRAZIL/USDC",
            levels=br_levels,
            mark_out=br_out,
            mode=out.mode,
            beta_const=br_beta,
            mark_model="ICE + β + Brazil EMA",
            fx_field=("fx_usdbrl", self._fx_usdbrl),
        )
        au_pair = _origin_pair_payload(
            pair_id="AUSTRALIA/USDC",
            levels=au_levels,
            mark_out=au_out,
            mode=out.mode,
            beta_const=au_beta,
            mark_model="ICE + β + Australia EMA",
            fx_field=("fx_usdaud", self._fx_usdaud),
        )

        payload = {
            **asdict(out),
            "pairs": {
                "US/USDC": us_pair,
                "BRAZIL/USDC": br_pair,
                "AUSTRALIA/USDC": au_pair,
            },
            "default_pair": DEFAULT_PAIR,
            "market": "US/USDC",
            "environment": "testnet",
            "network": "local",
            "fx_usdbrl": self._fx_usdbrl,
            "fx_usdaud": self._fx_usdaud,
            "beta_const_brazil": br_beta,
            "beta_const_australia": au_beta,
            "basis_structural_brazil": br_beta,
            "basis_structural_australia": au_beta,
            "basis_ema_brazil": br_out.basis_ema,
            "basis_ema_australia": au_out.basis_ema,
            "basis_traded_brazil": br_out.basis_traded,
            "basis_traded_australia": au_out.basis_traded,
            "mark_brazil_origin": br_out.mark,
            "mark_australia_origin": au_out.mark,
            "oracle_brazil_origin": br_out.oracle,
            "oracle_australia_origin": au_out.oracle,
            **us_levels,
        }
        self._latest_payload = payload
        await self._broadcast(payload)
