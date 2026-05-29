const VAULT_APY = 0.045;
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

function getAccount() {
  return window.CottonAuth?.getActiveAccount();
}

function getUser() {
  return window.CottonAuth?.getUser();
}

function totalAccountValue(account) {
  if (!account) return 0;
  return account.tradingBalance + account.ordersBalance + account.earningBalance + account.accruedYield;
}

function accrueYield(account) {
  if (!account) return;
  const now = Date.now();
  const elapsedSec = Math.max(0, (now - (account.lastAccrualTs || now)) / 1000);
  if (account.earningBalance > 0 && elapsedSec > 0) {
    const yieldDelta = account.earningBalance * (VAULT_APY / 365 / 86400) * elapsedSec;
    account.accruedYield = (account.accruedYield || 0) + yieldDelta;
  }
  account.lastAccrualTs = now;
  const user = getUser();
  if (user) window.CottonAuth.saveAccount(user.email, account);
}

function render() {
  const signedIn = window.CottonAuth?.isSignedIn();
  const account = getAccount();

  if (signedIn && account) accrueYield(account);

  const trading = signedIn ? account?.tradingBalance ?? 0 : 0;
  const orders = signedIn ? account?.ordersBalance ?? 0 : 0;
  const earning = signedIn ? account?.earningBalance ?? 0 : 0;
  const accrued = signedIn ? account?.accruedYield ?? 0 : 0;

  els.vaultApy.textContent = fmtPct(VAULT_APY);
  els.accruedYield.textContent = signedIn ? fmtUsdc(accrued, 4) : "—";
  els.totalValue.textContent = signedIn ? fmtUsdc(totalAccountValue(account)) : "—";
  els.tradingBalance.textContent = signedIn ? fmtUsdc(trading) : "Sign in to view";
  els.ordersBalance.textContent = signedIn ? fmtUsdc(orders) : "—";
  const earningText = signedIn ? fmtUsdc(earning) : "—";
  els.earningBalance.textContent = earningText;
  if (els.earningBalanceRow) els.earningBalanceRow.textContent = earningText;

  updateFormUi();
}

function availableForAction(account) {
  if (!account) return 0;
  return actionMode === "deposit"
    ? account.tradingBalance
    : account.earningBalance + (account.accruedYield || 0);
}

function updateFormUi() {
  const signedIn = window.CottonAuth?.isSignedIn();
  const account = getAccount();
  const avail = availableForAction(account);

  if (!signedIn) {
    els.earnFormHint.textContent = "Sign in to deposit or withdraw";
    els.earnSubmit.textContent = "Sign in to continue";
    els.earnSubmit.disabled = false;
    if (els.earnAmount) els.earnAmount.disabled = true;
    document.querySelectorAll(".earn-quick button").forEach((b) => {
      b.disabled = true;
    });
    return;
  }

  if (els.earnAmount) els.earnAmount.disabled = false;
  document.querySelectorAll(".earn-quick button").forEach((b) => {
    b.disabled = false;
  });

  els.earnFormHint.textContent =
    actionMode === "deposit"
      ? `Available to deposit: ${fmtUsdc(avail)}`
      : `Available to withdraw: ${fmtUsdc(avail)}`;
  els.earnSubmit.textContent =
    actionMode === "deposit" ? "Deposit to Earn" : "Withdraw to Trading";
  els.earnSubmit.classList.toggle("long", actionMode === "deposit");
  els.earnSubmit.classList.toggle("short", actionMode === "withdraw");
  els.earnSubmit.disabled = false;
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
  const account = getAccount();
  const avail = availableForAction(account);
  const amount = (avail * pct) / 100;
  if (els.earnAmount) {
    els.earnAmount.value = amount > 0 ? amount.toFixed(2) : "";
  }
}

function handleSubmit(e) {
  e.preventDefault();

  if (!window.CottonAuth?.isSignedIn()) {
    window.CottonAuth.openSignIn();
    return;
  }

  const user = getUser();
  const account = getAccount();
  if (!user || !account) return;

  const amount = Number(els.earnAmount?.value);
  if (!Number.isFinite(amount) || amount <= 0) {
    setMessage("Enter a valid amount.", "error");
    return;
  }

  if (actionMode === "deposit") {
    if (amount > account.tradingBalance + 1e-9) {
      setMessage("Insufficient trading balance.", "error");
      return;
    }
    account.tradingBalance -= amount;
    account.earningBalance = (account.earningBalance || 0) + amount;
    setMessage(`Deposited ${fmtUsdc(amount)} to Earn vault.`, "success");
  } else {
    const withdrawable = account.earningBalance + (account.accruedYield || 0);
    if (amount > withdrawable + 1e-9) {
      setMessage("Insufficient earning balance.", "error");
      return;
    }
    let remaining = amount;
    const fromYield = Math.min(account.accruedYield || 0, remaining);
    account.accruedYield = (account.accruedYield || 0) - fromYield;
    remaining -= fromYield;
    account.earningBalance -= remaining;
    account.tradingBalance += amount;
    setMessage(`Withdrew ${fmtUsdc(amount)} to Trading.`, "success");
  }

  window.CottonAuth.saveAccount(user.email, account);
  if (els.earnAmount) els.earnAmount.value = "";
  render();
}

function resetDemo() {
  if (!window.CottonAuth?.isSignedIn()) {
    window.CottonAuth.openSignIn();
    return;
  }
  const user = getUser();
  const account = getAccount();
  if (!user || !account) return;

  account.tradingBalance = window.CottonAuth.TESTNET_FUND_AMOUNT;
  account.ordersBalance = 0;
  account.earningBalance = 0;
  account.accruedYield = 0;
  account.positions = [];
  account.funded = true;
  account.lastAccrualTs = Date.now();
  window.CottonAuth.saveAccount(user.email, account);
  setMessage("Demo balances reset.", "info");
  render();
}

function onAuthChange() {
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

window.CottonAuth?.init({ onSignIn: onAuthChange, onSignOut: onAuthChange });
render();
setInterval(render, ACCRUAL_INTERVAL_MS);
