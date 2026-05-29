/**
 * cotton.xyz testnet onboarding — email sign-in + auto wallet (demo).
 * Swap to Privy when window.COTTON_PRIVY_APP_ID is configured (Phase 2b).
 */
(function () {
  const SESSION_KEY = "cotton_session_v1";
  const ACCOUNTS_KEY = "cotton_accounts_v1";
  const OTP_KEY = "cotton_otp_pending";
  const DEFAULT_TRADING = 0;
  const TESTNET_FUND_AMOUNT = 10_000;

  let onSignInCallback = null;
  let onSignOutCallback = null;

  function readJson(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch {
      return fallback;
    }
  }

  function writeJson(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
  }

  function normalizeEmail(email) {
    return String(email || "")
      .trim()
      .toLowerCase();
  }

  function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  }

  async function walletFromEmail(email) {
    const data = new TextEncoder().encode(`cotton-testnet:v1:${email}`);
    const hash = await crypto.subtle.digest("SHA-256", data);
    const hex = Array.from(new Uint8Array(hash))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
    return `0x${hex.slice(0, 40)}`;
  }

  function displayName(email) {
    return email.split("@")[0] || "Trader";
  }

  function shortAddress(addr) {
    if (!addr || addr.length < 10) return "—";
    return `${addr.slice(0, 6)}…${addr.slice(-4)}`;
  }

  function fmtUsdc(value, digits = 2) {
    if (!Number.isFinite(value)) return "—";
    return `${value.toLocaleString("en-US", {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    })} USDC`;
  }

  function getSession() {
    return readJson(SESSION_KEY, null);
  }

  function setSession(session) {
    if (session) writeJson(SESSION_KEY, session);
    else localStorage.removeItem(SESSION_KEY);
  }

  function loadAccounts() {
    return readJson(ACCOUNTS_KEY, {});
  }

  function saveAccounts(accounts) {
    writeJson(ACCOUNTS_KEY, accounts);
  }

  function defaultAccount(walletAddress) {
    return {
      walletAddress,
      tradingBalance: DEFAULT_TRADING,
      ordersBalance: 0,
      earningBalance: 0,
      accruedYield: 0,
      lastAccrualTs: Date.now(),
      positions: [],
      funded: false,
      createdAt: Date.now(),
    };
  }

  function getAccount(email) {
    const key = normalizeEmail(email);
    if (!key) return null;
    const accounts = loadAccounts();
    return accounts[key] || null;
  }

  function ensureAccount(email, walletAddress) {
    const key = normalizeEmail(email);
    const accounts = loadAccounts();
    if (!accounts[key]) {
      accounts[key] = defaultAccount(walletAddress);
      saveAccounts(accounts);
    }
    return accounts[key];
  }

  function saveAccount(email, account) {
    const key = normalizeEmail(email);
    const accounts = loadAccounts();
    accounts[key] = account;
    saveAccounts(accounts);
  }

  function getActiveAccount() {
    const session = getSession();
    if (!session?.email) return null;
    return ensureAccount(session.email, session.walletAddress);
  }

  function storeOtp(email, code) {
    sessionStorage.setItem(
      OTP_KEY,
      JSON.stringify({
        email: normalizeEmail(email),
        code,
        expires: Date.now() + 10 * 60 * 1000,
      }),
    );
  }

  function readOtp() {
    try {
      const raw = sessionStorage.getItem(OTP_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      if (parsed.expires < Date.now()) {
        sessionStorage.removeItem(OTP_KEY);
        return null;
      }
      return parsed;
    } catch {
      return null;
    }
  }

  function clearOtp() {
    sessionStorage.removeItem(OTP_KEY);
  }

  function generateCode() {
    return String(Math.floor(100000 + Math.random() * 900000));
  }

  // ── Modal UI ──

  let modalEl = null;
  let modalStep = "email";
  let pendingEmail = "";

  function ensureModal() {
    if (modalEl) return modalEl;

    modalEl = document.createElement("div");
    modalEl.className = "auth-modal hidden";
    modalEl.innerHTML = `
      <div class="auth-backdrop" data-auth-close></div>
      <div class="auth-dialog" role="dialog" aria-labelledby="auth-title" aria-modal="true">
        <button type="button" class="auth-close" data-auth-close aria-label="Close">×</button>
        <div class="auth-brand">
          <img src="./assets/cotton-logo.png" alt="" width="120" height="30" />
          <span class="auth-badge">Testnet</span>
        </div>
        <h2 id="auth-title" class="auth-title">Sign in to trade</h2>
        <p class="auth-sub" id="auth-sub">Use your email — we create a secure trading account for you. No crypto wallet needed.</p>

        <div class="auth-step" data-step="email">
          <label class="auth-field">
            <span>Email</span>
            <input type="email" id="auth-email" placeholder="you@company.com" autocomplete="email" />
          </label>
          <button type="button" class="auth-primary" id="auth-send-code">Continue</button>
        </div>

        <div class="auth-step hidden" data-step="code">
          <p class="auth-email-sent">Code sent to <strong id="auth-email-display"></strong></p>
          <div class="auth-demo-code" id="auth-demo-code"></div>
          <label class="auth-field">
            <span>Verification code</span>
            <input type="text" id="auth-code" inputmode="numeric" maxlength="6" placeholder="6-digit code" autocomplete="one-time-code" />
          </label>
          <button type="button" class="auth-primary" id="auth-verify">Sign in</button>
          <button type="button" class="auth-link" id="auth-back">Use a different email</button>
        </div>

        <div class="auth-step hidden" data-step="welcome">
          <div class="auth-welcome-icon">✓</div>
          <p class="auth-welcome-msg">Your account is ready.</p>
          <div class="auth-wallet-preview">
            <span class="auth-wallet-label">Trading account</span>
            <strong id="auth-wallet-short" class="auth-wallet-addr mono"></strong>
          </div>
          <p class="auth-balance-line">Balance: <strong id="auth-welcome-balance"></strong></p>
          <button type="button" class="auth-primary" id="auth-fund-btn">Get test funds ($10,000)</button>
          <button type="button" class="auth-secondary" id="auth-start-trading">Start trading</button>
        </div>

        <p class="auth-error hidden" id="auth-error"></p>
        <p class="auth-footnote">Testnet only · Simulated USDC · No real money</p>
      </div>
    `;
    document.body.appendChild(modalEl);

    modalEl.querySelector("#auth-send-code").addEventListener("click", handleSendCode);
    modalEl.querySelector("#auth-verify").addEventListener("click", handleVerify);
    modalEl.querySelector("#auth-back").addEventListener("click", () => showStep("email"));
    modalEl.querySelector("#auth-fund-btn").addEventListener("click", handleFundFromWelcome);
    modalEl.querySelector("#auth-start-trading").addEventListener("click", closeModal);
    modalEl.querySelectorAll("[data-auth-close]").forEach((el) => {
      el.addEventListener("click", closeModal);
    });

    return modalEl;
  }

  function showError(msg) {
    const el = ensureModal().querySelector("#auth-error");
    if (!msg) {
      el.classList.add("hidden");
      el.textContent = "";
      return;
    }
    el.textContent = msg;
    el.classList.remove("hidden");
  }

  function showStep(step) {
    modalStep = step;
    ensureModal().querySelectorAll(".auth-step").forEach((node) => {
      node.classList.toggle("hidden", node.dataset.step !== step);
    });
    showError("");
  }

  function openModal(step) {
    ensureModal();
    modalEl.classList.remove("hidden");
    document.body.classList.add("auth-modal-open");
    showStep(step || "email");
    if (step === "email") {
      const input = modalEl.querySelector("#auth-email");
      if (input) {
        input.value = pendingEmail || "";
        setTimeout(() => input.focus(), 50);
      }
    }
  }

  function closeModal() {
    if (!modalEl) return;
    modalEl.classList.add("hidden");
    document.body.classList.remove("auth-modal-open");
    showError("");
    renderNav();
    if (onSignInCallback && isSignedIn()) onSignInCallback(getUser());
  }

  async function handleSendCode() {
    const input = ensureModal().querySelector("#auth-email");
    const email = normalizeEmail(input?.value);
    if (!isValidEmail(email)) {
      showError("Please enter a valid email address.");
      return;
    }
    pendingEmail = email;
    const code = generateCode();
    storeOtp(email, code);

    ensureModal().querySelector("#auth-email-display").textContent = email;
    ensureModal().querySelector("#auth-demo-code").innerHTML =
      `Testnet demo — your code: <strong class="mono">${code.slice(0, 3)} ${code.slice(3)}</strong>`;

    showStep("code");
    const codeInput = ensureModal().querySelector("#auth-code");
    if (codeInput) {
      codeInput.value = "";
      setTimeout(() => codeInput.focus(), 50);
    }
  }

  async function handleVerify() {
    const email = pendingEmail;
    const codeInput = ensureModal().querySelector("#auth-code");
    const code = String(codeInput?.value || "").replace(/\s/g, "");
    const pending = readOtp();

    if (!pending || pending.email !== email) {
      showError("Code expired. Go back and request a new one.");
      return;
    }
    if (code !== pending.code) {
      showError("Incorrect code. Check the demo code shown above.");
      return;
    }

    clearOtp();
    const walletAddress = await walletFromEmail(email);
    const account = ensureAccount(email, walletAddress);

    setSession({
      email,
      walletAddress,
      displayName: displayName(email),
      signedInAt: Date.now(),
    });

    ensureModal().querySelector("#auth-wallet-short").textContent = shortAddress(walletAddress);
    ensureModal().querySelector("#auth-welcome-balance").textContent = fmtUsdc(
      account.tradingBalance + account.ordersBalance + account.earningBalance,
    );

    const fundBtn = ensureModal().querySelector("#auth-fund-btn");
    if (account.funded || account.tradingBalance >= TESTNET_FUND_AMOUNT) {
      fundBtn.classList.add("hidden");
    } else {
      fundBtn.classList.remove("hidden");
    }

    showStep("welcome");
    renderNav();
  }

  function handleFundFromWelcome() {
    fundTestAccount();
    const account = getActiveAccount();
    ensureModal().querySelector("#auth-welcome-balance").textContent = fmtUsdc(
      account.tradingBalance + account.ordersBalance + account.earningBalance,
    );
    ensureModal().querySelector("#auth-fund-btn").classList.add("hidden");
    renderNav();
    if (onSignInCallback) onSignInCallback(getUser());
  }

  // ── Account menu ──

  let menuEl = null;

  function closeMenu() {
    if (menuEl) menuEl.classList.add("hidden");
  }

  function toggleMenu(anchor) {
    if (!menuEl) {
      menuEl = document.createElement("div");
      menuEl.className = "auth-account-menu hidden";
      menuEl.innerHTML = `
        <div class="auth-menu-head">
          <strong id="auth-menu-name"></strong>
          <span id="auth-menu-email" class="auth-menu-email"></span>
        </div>
        <div class="auth-menu-balance">
          <span>Available</span>
          <strong id="auth-menu-balance" class="mono"></strong>
        </div>
        <button type="button" class="auth-menu-item" id="auth-menu-fund">Get test funds</button>
        <details class="auth-menu-advanced">
          <summary>Advanced</summary>
          <div class="auth-menu-addr">
            <span>Wallet</span>
            <code id="auth-menu-wallet" class="mono"></code>
          </div>
          <p class="auth-menu-note">Arbitrum Sepolia · embedded test wallet</p>
        </details>
        <button type="button" class="auth-menu-item auth-menu-signout" id="auth-menu-signout">Sign out</button>
      `;
      document.body.appendChild(menuEl);
      menuEl.querySelector("#auth-menu-fund").addEventListener("click", () => {
        fundTestAccount();
        renderNav();
        if (onSignInCallback) onSignInCallback(getUser());
      });
      menuEl.querySelector("#auth-menu-signout").addEventListener("click", () => {
        signOut();
      });
    }

    const user = getUser();
    const account = getActiveAccount();
    if (!user || !account) return;

    menuEl.querySelector("#auth-menu-name").textContent = user.displayName;
    menuEl.querySelector("#auth-menu-email").textContent = user.email;
    menuEl.querySelector("#auth-menu-balance").textContent = fmtUsdc(account.tradingBalance);
    menuEl.querySelector("#auth-menu-wallet").textContent = user.walletAddress;

    const fundBtn = menuEl.querySelector("#auth-menu-fund");
    fundBtn.classList.toggle("hidden", account.funded || account.tradingBalance >= TESTNET_FUND_AMOUNT);

    const rect = anchor.getBoundingClientRect();
    menuEl.style.top = `${rect.bottom + 6}px`;
    menuEl.style.right = `${Math.max(12, window.innerWidth - rect.right)}px`;
    menuEl.classList.toggle("hidden");

    if (!menuEl.classList.contains("hidden")) {
      const closeOnClick = (e) => {
        if (!menuEl.contains(e.target) && e.target !== anchor) {
          closeMenu();
          document.removeEventListener("click", closeOnClick);
        }
      };
      setTimeout(() => document.addEventListener("click", closeOnClick), 0);
    }
  }

  function renderNav() {
    document.querySelectorAll("[data-auth-nav]").forEach((slot) => {
      const signedIn = isSignedIn();
      const user = getUser();
      const account = getActiveAccount();

      if (signedIn && user) {
        slot.innerHTML = `
          <button type="button" class="auth-account-btn" id="auth-account-trigger">
            <span class="auth-account-name">${user.displayName}</span>
            <span class="auth-account-bal mono">${fmtUsdc(account?.tradingBalance ?? 0)}</span>
          </button>
        `;
        slot.querySelector("#auth-account-trigger")?.addEventListener("click", (e) => {
          e.stopPropagation();
          toggleMenu(e.currentTarget);
        });
      } else {
        slot.innerHTML = `<button type="button" class="hl-connect auth-signin-btn" id="auth-signin-btn">Sign in</button>`;
        slot.querySelector("#auth-signin-btn")?.addEventListener("click", () => openModal("email"));
      }
    });
  }

  // ── Public API ──

  function isSignedIn() {
    return Boolean(getSession()?.email);
  }

  function getUser() {
    const session = getSession();
    if (!session) return null;
    return session;
  }

  function signOut() {
    setSession(null);
    closeMenu();
    closeModal();
    renderNav();
    if (onSignOutCallback) onSignOutCallback();
  }

  function fundTestAccount() {
    const session = getSession();
    if (!session) return false;
    const account = ensureAccount(session.email, session.walletAddress);
    if (!account.funded && account.tradingBalance < TESTNET_FUND_AMOUNT) {
      account.tradingBalance = TESTNET_FUND_AMOUNT;
    }
    account.funded = true;
    saveAccount(session.email, account);
    return true;
  }

  function init(options = {}) {
    onSignInCallback = options.onSignIn || null;
    onSignOutCallback = options.onSignOut || null;
    renderNav();
    if (isSignedIn() && onSignInCallback) {
      onSignInCallback(getUser());
    }
  }

  window.CottonAuth = {
    init,
    isSignedIn,
    getUser,
    getActiveAccount,
    saveAccount,
    ensureAccount,
    fundTestAccount,
    openSignIn: () => openModal("email"),
    signOut,
    fmtUsdc,
    shortAddress,
    TESTNET_FUND_AMOUNT,
  };
})();
