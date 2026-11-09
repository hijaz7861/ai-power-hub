"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

type LedgerEntry = {
  id: number;
  amount: number;
  entry_type: string;
  description: string;
  created_at: string;
};

type Account = {
  user: { id: number; email: string; is_active: boolean };
  balance: { balance: number; unit: string };
  ledger: LedgerEntry[];
};

function createIdempotencyKey() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return "aiph-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2);
}

export default function AuthPanel() {
  const [account, setAccount] = useState<Account | null>(null);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [checking, setChecking] = useState(true);
  const [topupAmount, setTopupAmount] = useState("100");
  const [topupError, setTopupError] = useState("");
  const [topupBusy, setTopupBusy] = useState(false);

  const refreshAccount = useCallback(async () => {
    const response = await fetch("/api/account", { cache: "no-store" });
    if (!response.ok) {
      setAccount(null);
      return false;
    }
    setAccount((await response.json()) as Account);
    return true;
  }, []);

  useEffect(() => {
    refreshAccount().finally(() => setChecking(false));
  }, [refreshAccount]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (mode === "register") {
        const registration = await fetch("/api/auth/register", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ email, password }),
        });
        const registered = await registration.json().catch(() => ({}));
        if (!registration.ok) throw new Error(registered.detail || "Registration failed");
      }

      const login = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const loggedIn = await login.json().catch(() => ({}));
      if (!login.ok) throw new Error(loggedIn.detail || "Login failed");

      const loaded = await refreshAccount();
      if (!loaded) throw new Error("Signed in, but account data could not be loaded");
      window.dispatchEvent(new Event("aiph:auth-changed"));
      setPassword("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  async function startTopup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setTopupBusy(true);
    setTopupError("");
    try {
      const amount = Number(topupAmount);
      if (!Number.isInteger(amount) || amount < 100 || amount > 100000) {
        throw new Error("Top-up must be between PKR 100 and PKR 100,000.");
      }
      const response = await fetch("/api/payments/topups", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ amount_pkr: amount, idempotency_key: createIdempotencyKey() }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail || "Could not start checkout");
      if (result.checkout_url) {
        window.location.assign(result.checkout_url);
        return;
      }
      await refreshAccount();
    } catch (cause) {
      setTopupError(cause instanceof Error ? cause.message : "Top-up request failed");
    } finally {
      setTopupBusy(false);
    }
  }

  async function logout() {
    setBusy(true);
    try {
      await fetch("/api/auth/logout", { method: "POST" });
      setAccount(null);
      window.dispatchEvent(new Event("aiph:auth-changed"));
      setPassword("");
    } finally {
      setBusy(false);
    }
  }

  if (checking) return <section className="account-panel"><span className="account-muted">Checking account session…</span></section>;

  if (account) {
    return (
      <section className="account-panel">
        <div className="account-identity">
          <span className="account-avatar">{account.user.email.slice(0, 1).toUpperCase()}</span>
          <div><strong>{account.user.email}</strong><small>Signed in · secure server-managed session</small></div>
        </div>
        <div className="account-credit"><span>Available credits</span><strong>{account.balance.balance.toLocaleString()}</strong><small>≈ PKR {(account.balance.balance / 100).toFixed(2)}</small></div>
        <div className="account-actions">
          <a className="account-button secondary" href="/api/account/export">Download my data</a>
          <button className="account-button secondary" onClick={logout} disabled={busy}>Sign out</button>
        </div>
        <form className="topup-form" onSubmit={startTopup}>
          <label>Top up credits (PKR)
            <input type="number" min="100" max="100000" step="1" value={topupAmount} onChange={(event) => setTopupAmount(event.target.value)} />
          </label>
          <button className="account-button" type="submit" disabled={topupBusy}>{topupBusy ? "Preparing checkout…" : "Continue to secure payment"}</button>
          <small>Minimum PKR 100 · 1 credit = PKR 0.01 · payment confirmation is webhook-based</small>
          {topupError ? <p className="auth-error" role="alert">{topupError}</p> : null}
        </form>
        {account.ledger.length > 0 ? (
          <div className="ledger-preview">
            <strong>Recent credit activity</strong>
            {account.ledger.slice(0, 3).map((entry) => (
              <div className="ledger-row" key={entry.id}>
                <span><b>{entry.entry_type}</b><small>{entry.description}</small></span>
                <strong className={entry.amount >= 0 ? "ledger-positive" : "ledger-negative"}>{entry.amount > 0 ? "+" : ""}{entry.amount}</strong>
              </div>
            ))}
          </div>
        ) : <small className="account-muted">No credit activity recorded yet.</small>}
      </section>
    );
  }

  return (
    <section className="account-panel">
      <div className="auth-heading">
        <div><span className="eyebrow">YOUR ACCOUNT</span><h2>{mode === "login" ? "Welcome back" : "Create your account"}</h2></div>
        <div className="auth-switch">
          <button className={mode === "login" ? "selected" : ""} onClick={() => { setMode("login"); setError(""); }}>Sign in</button>
          <button className={mode === "register" ? "selected" : ""} onClick={() => { setMode("register"); setError(""); }}>Register</button>
        </div>
      </div>
      <form className="auth-form" onSubmit={submit}>
        <label>Email address<input type="email" autoComplete="email" required maxLength={320} value={email} onChange={(event) => setEmail(event.target.value)} /></label>
        <label>Password<input type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} required minLength={mode === "register" ? 12 : 1} maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} /></label>
        {mode === "register" ? <small className="account-muted">Use at least 12 characters. Your account starts with zero credits.</small> : null}
        {error ? <p className="auth-error" role="alert">{error}</p> : null}
        <button className="account-button" type="submit" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Sign in securely" : "Create account"}</button>
      </form>
    </section>
  );
}
