# Basis Layer Research — Brazil, Australia, India

**Purpose:** Identify cotton price references and data sources to begin designing **basis perps** (origin spread vs ICE Cotton No. 2).

**Anchor index (already in product):** ICE Cotton No. 2 (USD/lb)

**Basis definition (per origin):**

```text
Basis_origin = Local_Lint_Price_USD_per_lb − ICE_Cotton_No2_USD_per_lb
```

Positive basis = local origin trading at premium to ICE.  
Negative basis = discount to ICE.

---

## 1) Brazil

### Reference price
- **Primary domestic benchmark:** **CEPEA/ESALQ Index** (cotton lint / “pluma”, payment in 8 days)
- **Unit:** BRL per pound (also published in USD context via export parity)
- **Export reference:** FOB Santos quotes (US$/lb), tracked by Cepea

### Recent levels (public reports, 2026)
- CEPEA indicator: **~R$ 4.14/lb** (late Apr 2026) — highest nominal since mid-2025
- USD equivalent (Cepea): **~US$ 0.79/lb** (Apr 2026 avg)
- Export avg (May 2026 partial): **~US$ 0.70/lb**
- Reports note Brazil domestic/export quotes are often compared to **ICE first position** and **Cotlook A**

### Basis read
Brazil is a major export origin with counter-seasonal supply. Basis vs ICE moves with:
- BRL/USD
- export parity vs domestic spot
- China import demand
- crop size (CONAB/USDA)

USDA Cotton: World Markets and Trade has cited Brazil basis vs ICE around **+500 points** in some periods (vs **−300** year prior) — highly variable.

### Data sources (start here)
| Source | URL | Use |
|--------|-----|-----|
| **Cepea** (ESALQ-USP) | https://cepea.org.br | Daily/weekly lint index, export parity, USD series |
| **Secex** export stats | via Cepea reports | Export volume/price validation |
| **CONAB** | https://www.conab.gov.br | Crop/supply context for basis moves |
| **USDA FAS** | Cotton: World Markets and Trade | Brazil price + basis commentary |

### Basis product sketch
- **`BRAZIL-BASIS-USDC` perpetual**
- Oracle: CEPEA lint (USD/lb) − ICE No. 2
- Fallback: order-book EMA when CEPEA stale (weekends/holidays)

---

## 2) Australia

### Reference price
Australian lint is **explicitly priced as ICE + basis** (industry standard):

```text
AUD_cash_price = ((ICE_US¢/lb + Basis_US¢/lb) × 500 lb/bale) / FX_forward
```

- **ICE Cotton No. 2** = hedge benchmark
- **Basis** = premium/discount for grade (e.g. 31-3-36 vs ICE 41-4-34), location (FOT gin), timing (May–Jul window)
- Basis quoted in **points** (100 points = 1 US cent/lb)

### Example (industry guide)
- ICE Jul: **71.6 ¢/lb**
- Basis: **+300 points** (+3.0 ¢/lb)
- Local US¢/lb: **74.6 ¢/lb**

Recent market reports (2025) showed ICE range often **65–70 ¢/lb** with active mill buying; basis varies by season/quality/water.

### Basis read
Australia often correlates well with ICE (academic work cited AU among higher hedge-ratio origins), but **local basis still moves** on:
- Murray–Darling water / drought
- harvest timing (May–Jul)
- export demand (China, Vietnam, etc.)
- AUD/USD

### Data sources (start here)
| Source | URL | Use | Reliability |
|--------|-----|-----|-------------|
| **ABARES weekly commodity update** | https://www.agriculture.gov.au/abares/data/weekly-commodity-price-update | Cotlook A (USc/lb), AUD/USD — **live governance** | High (gov, weekly) |
| **Cotton Australia / cottoninfo** | https://cottoninfo.com.au | Pricing guides, basis education | High (methodology) |
| **CSD** (Cotton Seed Distributors) | https://csd.net.au | Worked examples ICE + basis + FX | High (examples) |
| **Australian Cotton Shippers Association** | https://austcottonshippers.com.au | Market reports | Medium (qualitative) |
| **ICE Cotton No. 2** | — | Anchor futures | High |
| **USDA FAS** | — | AU production/export context | Medium |

### Data reliability vs Brazil (MVP assessment)

| Dimension | Australia | Brazil (CEPEA) |
|-----------|-----------|----------------|
| Live access | ABARES weekly, no scrape blocks | CEPEA direct scrape 403; CSV stale (2018) |
| Pricing model | Explicit ICE + basis (¢/lb) | CEPEA daily index (BRL → USD) |
| Historical daily series | **No free AU-local lint index** | CEPEA daily 2000–2018 (royopa CSV) |
| Backtest calibration | Provisional β from industry guides | 504d CEPEA−ICE median (~9¢/lb) |

**cotton.xyz MVP:** AUSTRALIA/USDC uses same v4 engine (ICE + β_const + book EMA). β_const ~+2.8¢/lb provisional until ABARES AUD/bale series is wired.

### Basis product sketch
- **`AU-BASIS-USDC` perpetual**
- Oracle: (ICE + merchant basis survey or ACGA-style benchmark) − ICE = **basis only**
- Note: basis may be sourced directly in ¢/lb from industry quotes if available

---

## 3) India

### Reference price
India uses **multiple** references (policy + market):

| Index | What it is | Unit | Perp fit |
|-------|------------|------|----------|
| **MSP** (govt) | Minimum Support Price for seed cotton | ₹/quintal (100 kg) | Policy floor — not ideal alone for lint perp |
| **ICS 105** | Indian Cotton Standard lint grade | market quotes | **Strong candidate** |
| **MCX Cotton Futures** | Exchange-traded contract (re-launched 2023) | ₹/candy or contract spec | Hedge/discovery layer |
| **CAI basis reports** | ICS 105 vs ICE & vs Cotlook A | basis tables/charts | **Best starting point for basis perp** |

### MSP (2025–26 season)
- Medium staple: **₹7,710/quintal**
- Long staple: **₹8,110/quintal**

### MSP (2026–27 approved)
- Medium staple: **₹8,267/quintal**
- Long staple: **₹8,667/quintal**

⚠️ MSP is **seed cotton**, not lint USD/lb — requires conversion/normalization before merging with ICE.

### CAI basis monitoring (high value)
Cotton Association of India publishes recurring reports:
- **“Basis Comparison of ICS 105 with ICE Futures”**
- **“Basis Comparison of ICS 105 with Cotlook A Index”**

Source: https://caionline.in (News section — weekly/bi-weekly)

### Basis read
India basis is heavily influenced by:
- MSP/CCI procurement
- import duties / trade policy
- domestic mill demand
- speculative periods (2022 spike noted in trade press)

USDA has cited India lint near **~88 ¢/lb** with basis to ICE **~+1,700 points** in some months — very wide vs other origins.

### Data sources (start here)
| Source | URL | Use |
|--------|-----|-----|
| **CAI** | https://caionline.in | ICS 105 vs ICE basis (primary) |
| **MCX** | https://www.mcxindia.com | Futures reference / eventual API |
| **CCI** | Cotton Corporation of India | MSP procurement context |
| **Ministry/agri releases** | press releases | MSP updates |
| **USDA FAS** | India cotton chapter | Basis commentary |

### Basis product sketch
- **`INDIA-BASIS-USDC` perpetual**
- Oracle: ICS 105 (USD/lb normalized) − ICE No. 2
- Start with **CAI published basis** as sanity check feed
- Handle INR conversion + stale hours explicitly

---

## 4) Cross-origin comparison (why basis perps matter)

| Origin | Typical relationship to ICE | Main basis drivers |
|--------|----------------------------|--------------------|
| **Brazil** | Often competitive export discount/premium vs ICE | FX, export parity, China demand, crop size |
| **Australia** | Structured as ICE + basis | Water, grade, AUD, export program |
| **India** | Frequent wide premium periods | MSP, policy, domestic mill demand, duties |
| **US (anchor)** | ICE deliverable | Domestic stocks, weather, export policy |

ICE alone is **not a perfect hedge** for non-US origins (especially India/Brazil policy cycles). This validates your **basis perp** roadmap.

---

## 5) Recommended MVP data architecture (TEST → Live Testnet)

### Phase A — Research feeds (now, no trading)
1. **ICE Cotton No. 2** — anchor (already simulated; later live feed)
2. **Brazil** — Cepea lint USD/lb (or BRL + FX conversion)
3. **Australia** — ICE + reported basis (¢/lb) from industry/market reports initially
4. **India** — CAI ICS 105 vs ICE basis series

Store daily:
- `ice_usd_lb`
- `brazil_lint_usd_lb`, `brazil_basis`
- `australia_basis_cents_lb`
- `india_ics105_usd_lb`, `india_basis`

### Phase B — Basis oracle (pre–Live Testnet)
- Publish `basis_oracle` per origin on relayer
- Mark for basis perp = EMA-smoothed basis + clamp
- 24/7 fallback when origin feed stale (carry last basis + order-book pressure)

### Phase C — Basis perps (Arbitrum Sepolia)
- `cotton-USDC` (index)
- `BRAZIL-BASIS-USDC`
- `AU-BASIS-USDC`
- `INDIA-BASIS-USDC`

---

## 6) Immediate next steps (low effort, high signal)

1. **Subscribe/track CAI basis PDFs** (India) — weekly validation dataset  
2. **Pull Cepea cotton lint series** (Brazil) — daily CSV/Excel from database  
3. **Document AU basis range** from CSD/cottoninfo examples + merchant quotes  
4. **Build `basis-monitor` script** (Python) that outputs:
   - ICE (mock/live)
   - origin price
   - computed basis
   - % deviation from 30-day mean  
5. Add dashboard panel on test trade UI: **Basis Monitor (read-only)**

---

## 7) Important caveats

- **Units differ** (₹/quintal seed vs ¢/lb lint) — normalize before on-chain oracle  
- **Grades differ** (ICS 105, AU 31-3-36, Brazil pluma quality bands) — document fixed grade assumptions  
- **Timestamps/timezones** — Brazil/India/AU market hours ≠ ICE  
- **Policy floors (India MSP)** can decouple physical from global for periods  
- All non-ICE feeds need **staleness rules** for 24/7 perp marks  

---

## 8) Sources consulted

- Cepea (Brazil lint index & export parity reports)
- Cotton Association of India (ICS 105 basis vs ICE)
- Cotton Info Australia / CSD (ICE + basis pricing formula)
- USDA FAS — Cotton: World Markets and Trade
- MCX India cotton futures launch (2023)
- Government of India MSP announcements (2025–26, 2026–27)
