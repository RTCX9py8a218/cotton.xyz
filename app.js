const API_BASE = window.COTTON_API_BASE || "http://localhost:8000";
const WS_URL = API_BASE.replace(/^http/, "ws") + "/ws/market";
const CANDLE_INTERVAL_S = 60;
const SEED_CANDLE_COUNT = 90;
const EMA_FAST = 9;
const EMA_SLOW = 21;

const PAIR_META = {
  "US/USDC": {
    title: "US/USDC",
    sub: "ICE Cotton No. 2 · 1m",
  },
  "BRAZIL/USDC": {
    title: "BRAZIL/USDC",
    sub: "ICE + β · Brazil book · 1m",
  },
  "AUSTRALIA/USDC": {
    title: "AUSTRALIA/USDC",
    sub: "ICE + β · Australia book · 1m",
  },
};

let activePair = "US/USDC";
let lastPayload = null;

const els = {
  conn: document.getElementById("conn-status"),
  mark: document.getElementById("mark"),
  oracle: document.getElementById("oracle"),
  externalPrice: document.getElementById("external-price"),
  iceAnchor: document.getElementById("ice-anchor"),
  basisModel: document.getElementById("basis-model"),
  basisEma: document.getElementById("basis-ema"),
  fxUsdbrl: document.getElementById("fx-usdbrl"),
  fxUsdaud: document.getElementById("fx-usdaud"),
  spread: document.getElementById("spread"),
  funding: document.getElementById("funding"),
  change24h: document.getElementById("change-24h"),
  oracleMode: document.getElementById("oracle-mode"),
  mid: document.getElementById("mid"),
  ipd: document.getElementById("ipd"),
  c1: document.getElementById("c1"),
  c2: document.getElementById("c2"),
  c3: document.getElementById("c3"),
  impactBid: document.getElementById("impact-bid"),
  impactAsk: document.getElementById("impact-ask"),
  lastTrade: document.getElementById("last-trade"),
  bookAsks: document.getElementById("book-asks"),
  bookBids: document.getElementById("book-bids"),
  bookMidPrice: document.getElementById("book-mid-price"),
  bookSpread: document.getElementById("book-spread"),
  estEntry: document.getElementById("est-entry"),
  chartContainer: document.getElementById("candle-chart"),
  chartTitle: document.getElementById("chart-title"),
  chartSub: document.getElementById("chart-sub"),
  marketSymbol: document.getElementById("market-symbol"),
  pairMenu: document.getElementById("pair-menu"),
  pairTrigger: document.getElementById("pair-trigger"),
};

const chartState = {
  baseline: null,
  seeded: false,
  currentBucket: null,
  currentCandle: null,
  candles: [],
};

let tvChart = null;
let candleSeries = null;
let ema9Series = null;
let ema21Series = null;

const fmt = (value, digits = 4) =>
  typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "—";

const fmtInt = (value) =>
  typeof value === "number" && Number.isFinite(value)
    ? Math.round(value).toLocaleString("en-US")
    : "—";

const fmtPct = (value, digits = 4) =>
  typeof value === "number" && Number.isFinite(value)
    ? `${value >= 0 ? "+" : ""}${value.toFixed(digits)}%`
    : "—";

function bucketTime(ts) {
  return Math.floor(ts / CANDLE_INTERVAL_S) * CANDLE_INTERVAL_S;
}

function setFeedStatus(kind, label) {
  els.conn.className = `hl-status feed-${kind}`;
  els.conn.textContent = label;
}

function togglePairMenu(open) {
  if (!els.pairMenu || !els.pairTrigger) return;
  const show = open ?? els.pairMenu.classList.contains("hidden");
  els.pairMenu.classList.toggle("hidden", !show);
  els.pairTrigger.setAttribute("aria-expanded", show ? "true" : "false");
}

function initChart() {
  if (!els.chartContainer || typeof LightweightCharts === "undefined") return;

  tvChart = LightweightCharts.createChart(els.chartContainer, {
    layout: {
      background: { color: "#0b0e11" },
      textColor: "#7d8590",
      fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
      fontSize: 11,
    },
    grid: {
      vertLines: { color: "rgba(255,255,255,0.04)" },
      horzLines: { color: "rgba(255,255,255,0.04)" },
    },
    rightPriceScale: {
      borderColor: "rgba(255,255,255,0.06)",
    },
    timeScale: {
      borderColor: "rgba(255,255,255,0.06)",
      timeVisible: true,
      secondsVisible: false,
    },
    crosshair: {
      mode: LightweightCharts.CrosshairMode.Normal,
      vertLine: { color: "rgba(80,210,193,0.35)" },
      horzLine: { color: "rgba(80,210,193,0.35)" },
    },
  });

  candleSeries = tvChart.addCandlestickSeries({
    upColor: "#3fdca4",
    downColor: "#ff5c5c",
    borderUpColor: "#3fdca4",
    borderDownColor: "#ff5c5c",
    wickUpColor: "#3fdca4",
    wickDownColor: "#ff5c5c",
  });

  ema9Series = tvChart.addLineSeries({
    color: "#50d2c1",
    lineWidth: 1,
    priceLineVisible: false,
    lastValueVisible: true,
    title: "EMA 9",
  });

  ema21Series = tvChart.addLineSeries({
    color: "#6b8afd",
    lineWidth: 1,
    priceLineVisible: false,
    lastValueVisible: true,
    title: "EMA 21",
  });

  const resize = () => {
    if (!tvChart || !els.chartContainer) return;
    tvChart.applyOptions({
      width: els.chartContainer.clientWidth,
      height: Math.max(300, els.chartContainer.clientHeight),
    });
  };

  resize();
  window.addEventListener("resize", resize);
}

function emaMultiplier(period) {
  return 2 / (period + 1);
}

function buildEmaSeries(candles, period) {
  const k = emaMultiplier(period);
  const series = [];
  let ema = null;

  for (const candle of candles) {
    if (ema === null) {
      ema = candle.close;
    } else {
      ema = candle.close * k + ema * (1 - k);
    }
    series.push({ time: candle.time, value: ema });
  }

  return series;
}

function allCandlesIncludingCurrent() {
  const candles = [...chartState.candles];
  if (chartState.currentCandle) {
    candles.push({ ...chartState.currentCandle });
  }
  return candles;
}

function refreshEmas() {
  if (!ema9Series || !ema21Series) return;

  const candles = allCandlesIncludingCurrent();
  if (candles.length === 0) return;

  ema9Series.setData(buildEmaSeries(candles, EMA_FAST));
  ema21Series.setData(buildEmaSeries(candles, EMA_SLOW));
}

function seedCandles(endPrice, endTs) {
  const endBucket = bucketTime(endTs);
  const candles = [];
  let price = endPrice;

  for (let i = SEED_CANDLE_COUNT; i >= 1; i -= 1) {
    const time = endBucket - i * CANDLE_INTERVAL_S;
    const open = price;
    const delta = (Math.random() - 0.5) * 0.18;
    const close = Math.max(0.01, open + delta);
    const high = Math.max(open, close) + Math.random() * 0.06;
    const low = Math.min(open, close) - Math.random() * 0.06;
    candles.push({ time, open, high, low, close });
    price = close;
  }

  chartState.candles = candles;
  chartState.seeded = true;
  if (candleSeries) candleSeries.setData(candles);
  refreshEmas();
}

function pushCandle(candle) {
  if (!candleSeries) return;
  candleSeries.update(candle);
}

function updateCandles(mark, ts) {
  const bucket = bucketTime(ts);

  if (!chartState.seeded) {
    seedCandles(mark, ts);
    chartState.baseline = mark;
  }

  if (chartState.currentBucket === null || chartState.currentCandle === null) {
    chartState.currentBucket = bucket;
    chartState.currentCandle = {
      time: bucket,
      open: mark,
      high: mark,
      low: mark,
      close: mark,
    };
    pushCandle(chartState.currentCandle);
    refreshEmas();
    return;
  }

  if (bucket > chartState.currentBucket) {
    chartState.candles.push({ ...chartState.currentCandle });
    if (chartState.candles.length > 500) chartState.candles.shift();

    chartState.currentBucket = bucket;
    chartState.currentCandle = {
      time: bucket,
      open: mark,
      high: mark,
      low: mark,
      close: mark,
    };
    pushCandle(chartState.currentCandle);
    refreshEmas();
    return;
  }

  chartState.currentCandle.high = Math.max(chartState.currentCandle.high, mark);
  chartState.currentCandle.low = Math.min(chartState.currentCandle.low, mark);
  chartState.currentCandle.close = mark;
  pushCandle(chartState.currentCandle);
  refreshEmas();
}

function renderOrderBook(bids = [], asks = []) {
  const rowHtml = (row, maxCum, side) => {
    const depthPct = (row.cumulative / maxCum) * 100;
    return `
      <div class="book-row ${side}">
        <div class="book-depth" style="width:${depthPct.toFixed(1)}%"></div>
        <span class="book-cell price">${fmt(row.price)}</span>
        <span class="book-cell size">${fmt(row.size, 1)}</span>
        <span class="book-cell total">${fmtInt(row.notional)}</span>
      </div>`;
  };

  const enrich = (rows) => {
    let cumulative = 0;
    return rows.map((row) => {
      cumulative += row.size;
      return {
        ...row,
        cumulative,
        notional: row.price * row.size,
      };
    });
  };

  const askEnriched = enrich(asks);
  const bidEnriched = enrich(bids);
  const askMax = Math.max(1, askEnriched.at(-1)?.cumulative ?? 1);
  const bidMax = Math.max(1, bidEnriched.at(-1)?.cumulative ?? 1);

  els.bookAsks.innerHTML = [...askEnriched]
    .reverse()
    .map((row) => rowHtml(row, askMax, "ask"))
    .join("");
  els.bookBids.innerHTML = bidEnriched.map((row) => rowHtml(row, bidMax, "bid")).join("");
}

function resetChartForPair() {
  chartState.baseline = null;
  chartState.seeded = false;
  chartState.currentBucket = null;
  chartState.currentCandle = null;
  chartState.candles = [];
  if (candleSeries) candleSeries.setData([]);
  if (ema9Series) ema9Series.setData([]);
  if (ema21Series) ema21Series.setData([]);
}

function resolvePairView(data) {
  const pair = data.pairs?.[activePair];
  if (!pair) {
    return {
      ...data,
      pair: activePair,
    };
  }
  return {
    ...data,
    ...pair,
    bids: pair.bids || data.bids,
    asks: pair.asks || data.asks,
  };
}

const ORIGIN_PAIRS = new Set(["BRAZIL/USDC", "AUSTRALIA/USDC"]);

function isOriginPair(pairId) {
  return ORIGIN_PAIRS.has(pairId);
}

function setActivePair(pairId) {
  if (pairId === activePair) {
    togglePairMenu(false);
    return;
  }
  activePair = pairId;
  resetChartForPair();
  togglePairMenu(false);

  document.querySelectorAll(".pair-btn").forEach((btn) => {
    const selected = btn.dataset.pair === pairId;
    btn.classList.toggle("active", selected);
    btn.setAttribute("aria-selected", selected ? "true" : "false");
  });

  if (els.marketSymbol) els.marketSymbol.textContent = pairId;

  document.querySelectorAll(".origin-only").forEach((el) => {
    const fxPair = el.dataset.fxPair;
    if (fxPair) {
      el.classList.toggle("hidden", pairId !== fxPair);
    } else {
      el.classList.toggle("hidden", !isOriginPair(pairId));
    }
  });

  const meta = PAIR_META[pairId] || PAIR_META["US/USDC"];
  if (els.chartTitle) els.chartTitle.textContent = meta.title;
  if (els.chartSub) els.chartSub.textContent = meta.sub;

  if (lastPayload) renderUpdate(lastPayload);
}

function renderUpdate(data) {
  try {
    lastPayload = data;
    const view = resolvePairView(data);
    const bestBid = Number(view.best_bid);
    const bestAsk = Number(view.best_ask);
    const mid = Number(view.mid);
    const spreadAbs =
      Number.isFinite(bestBid) && Number.isFinite(bestAsk) ? bestAsk - bestBid : 0;
    const spreadBps = mid > 0 ? (spreadAbs / mid) * 10_000 : 0;

    if (chartState.baseline == null && chartState.seeded) {
      chartState.baseline = view.mark;
    }

    updateCandles(view.mark, view.ts);

    const changePct =
      chartState.baseline > 0
        ? ((view.mark - chartState.baseline) / chartState.baseline) * 100
        : 0;

    els.mark.textContent = fmt(view.mark);
    els.oracle.textContent = fmt(view.oracle);
    els.externalPrice.textContent =
      view.external_price == null ? "—" : fmt(view.external_price);
    if (els.iceAnchor) els.iceAnchor.textContent = fmt(view.ice_anchor ?? data.oracle);
    if (els.basisModel) {
      const b =
        view.basis_structural ??
        (activePair === "AUSTRALIA/USDC"
          ? data.basis_structural_australia
          : data.basis_structural_brazil);
      els.basisModel.textContent = fmt(b, 4);
    }
    if (els.basisEma) {
      const ema =
        view.basis_ema ??
        (activePair === "AUSTRALIA/USDC"
          ? data.basis_ema_australia
          : data.basis_ema_brazil);
      els.basisEma.textContent = fmt(ema, 4);
    }
    if (els.fxUsdbrl) els.fxUsdbrl.textContent = fmt(view.fx_usdbrl ?? data.fx_usdbrl, 4);
    if (els.fxUsdaud) els.fxUsdaud.textContent = fmt(view.fx_usdaud ?? data.fx_usdaud, 4);
    els.spread.textContent = `${fmt(spreadAbs, 4)} (${spreadBps.toFixed(1)} bps)`;
    els.mid.textContent = fmt(view.mid);
    els.ipd.textContent = view.ipd != null ? fmt(view.ipd, 6) : "—";
    els.c1.textContent = fmt(view.c1);
    els.c2.textContent = fmt(view.c2);
    els.c3.textContent = fmt(view.c3);
    els.impactBid.textContent = fmt(view.impact_bid);
    els.impactAsk.textContent = fmt(view.impact_ask);
    els.lastTrade.textContent = fmt(view.last_trade);
    els.bookMidPrice.textContent = fmt(view.mid);
    els.bookSpread.textContent = `${fmt(spreadAbs, 4)} · ${spreadBps.toFixed(1)} bps`;
    els.estEntry.textContent = fmt(view.mark);

    els.change24h.textContent = fmtPct(changePct, 3);
    els.change24h.className = `hl-stat-value mono ${changePct >= 0 ? "up" : "down"}`;
    els.mark.className = `hl-stat-value mono ${changePct >= 0 ? "up" : "down"}`;

    const isTestnet = view.environment === "testnet" || view.network === "local";
    if (view.mode === "external") {
      setFeedStatus("online", isTestnet ? "Live" : "External");
      els.oracleMode.textContent = "External";
    } else {
      setFeedStatus("fallback", isTestnet ? "Fallback" : "Fallback");
      els.oracleMode.textContent = "Fallback";
    }

    renderOrderBook(view.bids || [], view.asks || []);
  } catch (err) {
    console.error("renderUpdate failed", err);
    setFeedStatus("offline", "Feed Error");
  }
}

async function bootstrapFromRest() {
  try {
    const res = await fetch(`${API_BASE}/api/market/latest`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const body = await res.json();
    if (body.ready && body.data) {
      renderUpdate(body.data);
      return true;
    }
    setFeedStatus("offline", "Waiting for feed");
    return false;
  } catch {
    setFeedStatus("offline", "API offline — start backend");
    return false;
  }
}

function connectWs() {
  setFeedStatus("offline", "Connecting");
  let ws;
  try {
    ws = new WebSocket(WS_URL);
  } catch {
    setFeedStatus("offline", "WS failed");
    setTimeout(connectWs, 1500);
    return;
  }

  ws.onopen = () => setFeedStatus("online", "Live");

  ws.onmessage = (event) => {
    try {
      renderUpdate(JSON.parse(event.data));
    } catch {
      setFeedStatus("offline", "Parse Error");
    }
  };

  ws.onclose = () => {
    setFeedStatus("offline", "Reconnecting…");
    setTimeout(connectWs, 1500);
  };

  ws.onerror = () => ws.close();
}

document.querySelectorAll(".pair-btn").forEach((btn) => {
  btn.addEventListener("click", () => setActivePair(btn.dataset.pair));
});

if (els.pairTrigger) {
  els.pairTrigger.addEventListener("click", (e) => {
    e.stopPropagation();
    togglePairMenu();
  });
}

document.addEventListener("click", () => togglePairMenu(false));
if (els.pairMenu) {
  els.pairMenu.addEventListener("click", (e) => e.stopPropagation());
}

document.querySelectorAll(".side-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".side-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const submit = document.querySelector(".submit-btn");
    if (!submit) return;
    submit.classList.remove("long", "short");
    submit.classList.add(btn.dataset.side);
    submit.textContent =
      btn.dataset.side === "long" ? "Connect wallet to long" : "Connect wallet to short";
  });
});

initChart();
bootstrapFromRest();
connectWs();
