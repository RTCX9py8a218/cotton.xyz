const STORAGE_KEY = "cotton_earn_state_v1";
const VAULT_APY = 0.045;
const DEFAULT_TRADING = 10_000;
const ACCRUAL_INTERVAL_MS = 2000;

const els = {
  vaultApy: document.getElementById("vault-apy"),
  accruedYield: document.getElementById("accrued-yield"),
  totalValue: document.getElementById("total-value"),
  tradingBalance: document.getElementById("trading-balance"),
  ordersBalance: document.getElementById("orders-balance"),
  earningBalance: document.getElementById("earning-balance"),
  earningBalanceRow: document.getElementById("earning-balance-row"),
  earnAmount: document.getElementById("earn-amount"),
  earnForm: document.getElementById("earn-form"),
  earnFormHint: document.getElementById("earn-form-hint"),
  earnSubmit: document.getElementById("earn-submit"),
  earnMessage: document.getElementById("earn-message"),
  resetDemo: document.getElementById("reset-demo"),
};

let actionMode = "deposit";
let state = loadState();

function loadState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      return normalizeState(parsed);
    }
  } catch {
    /* use default */
  }
  return defaultState();
}

function defaultState() {
  return {
    tradingBalance: DEFAULT_TRADING,
    ordersBalance: 0,
    earningBalance: 0,
    accruedYield: 0,
    lastAccrualTs: Date.now(),
  };
}

function normalizeState(s) {
  return {
    tradingBalance: num(s.tradingBalance, DEFAULT_TRADING),
    ordersBalance: num(s.ordersBalance, 0),
    earningBalance: num(s.earningBalance, 0),
    accruedYield: num(s.accruedYield, 0),
    lastAccrualTs: num(s.lastAccrualTs, Date.now()),
  };
}

function num(v, fallback) {
  const n = Number(v);
  return Number.isFinite(n) ? n : fallback;
}

function saveState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function fmtUsdc(value, digits = 2) {
  if (!Number.isFinite(value)) return "—";
  return `${value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })} USDC`;
}

function fmtPct(value) {
  return `${(value * 100).toFixed(2)}%`;
}

function totalAccountValue() {
  return state.tradingBalance + state.ordersBalance + state.earningBalance + state.accruedYield;
}

function accrueYield() {
  const now = Date.now();
  const elapsedSec = Math.max(0, (now - state.lastAccrualTs) / 1000);
  if (state.earningBalance > 0 && elapsedSec > 0) {
    const yieldDelta = state.earningBalance * (VAULT_APY / 365 / 86400) * elapsedSec;
    state.accruedYield += yieldDelta;
  }
  state.lastAccrualTs = now;
  saveState();
}

function render() {
  accrueYield();

  els.vaultApy.textContent = fmtPct(VAULT_APY);
  els.accruedYield.textContent = fmtUsdc(state.accruedYield, 4);
  els.totalValue.textContent = fmtUsdc(totalAccountValue());
  els.tradingBalance.textContent = fmtUsdc(state.tradingBalance);
  els.ordersBalance.textContent = fmtUsdc(state.ordersBalance);
  const earningText = fmtUsdc(state.earningBalance);
  els.earningBalance.textContent = earningText;
  if (els.earningBalanceRow) els.earningBalanceRow.textContent = earningText;

  updateFormUi();
}

function availableForAction() {
  return actionMode === "deposit"
    ? state.tradingBalance
    : state.earningBalance + state.accruedYield;
}

function updateFormUi() {
  const avail = availableForAction();
  els.earnFormHint.textContent =
    actionMode === "deposit"
      ? `Available to deposit: ${fmtUsdc(avail)}`
      : `Available to withdraw: ${fmtUsdc(avail)}`;
  els.earnSubmit.textContent =
    actionMode === "deposit" ? "Deposit to Earn" : "Withdraw to Trading";
  els.earnSubmit.classList.toggle("long", actionMode === "deposit");
  els.earnSubmit.classList.toggle("short", actionMode === "withdraw");
}

function setMessage(text, kind = "info") {
  if (!els.earnMessage) return;
  els.earnMessage.textContent = text;
  els.earnMessage.dataset.kind = kind;
}

function setActionMode(mode) {
  actionMode = mode;
  document.querySelectorAll(".earn-action-tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.action === mode);
  });
  if (els.earnAmount) els.earnAmount.value = "";
  updateFormUi();
  setMessage("");
}

function applyQuickPct(pct) {
  const avail = availableForAction();
  const amount = (avail * pct) / 100;
  if (els.earnAmount) {
    els.earnAmount.value = amount > 0 ? amount.toFixed(2) : "";
  }
}

function handleSubmit(e) {
  e.preventDefault();
  const amount = Number(els.earnAmount?.value);
  if (!Number.isFinite(amount) || amount <= 0) {
    setMessage("Enter a valid amount.", "error");
    return;
  }

  if (actionMode === "deposit") {
    if (amount > state.tradingBalance + 1e-9) {
      setMessage("Insufficient trading balance.", "error");
      return;
    }
    state.tradingBalance -= amount;
    state.earningBalance += amount;
    setMessage(`Deposited ${fmtUsdc(amount)} to Earn vault.`, "success");
  } else {
    const withdrawable = state.earningBalance + state.accruedYield;
    if (amount > withdrawable + 1e-9) {
      setMessage("Insufficient earning balance.", "error");
      return;
    }
    let remaining = amount;
    const fromYield = Math.min(state.accruedYield, remaining);
    state.accruedYield -= fromYield;
    remaining -= fromYield;
    state.earningBalance -= remaining;
    state.tradingBalance += amount;
    setMessage(`Withdrew ${fmtUsdc(amount)} to Trading.`, "success");
  }

  if (els.earnAmount) els.earnAmount.value = "";
  saveState();
  render();
}

function resetDemo() {
  state = defaultState();
  saveState();
  setMessage("Demo balances reset.", "info");
  render();
}

document.querySelectorAll(".earn-action-tab").forEach((btn) => {
  btn.addEventListener("click", () => setActionMode(btn.dataset.action));
});

document.querySelectorAll(".earn-quick button").forEach((btn) => {
  btn.addEventListener("click", () => applyQuickPct(Number(btn.dataset.pct)));
});

els.earnForm?.addEventListener("submit", handleSubmit);
els.resetDemo?.addEventListener("click", resetDemo);

render();
setInterval(render, ACCRUAL_INTERVAL_MS);
