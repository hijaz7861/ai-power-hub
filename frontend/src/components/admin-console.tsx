"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

type SupplierOffer = {
  id: number;
  supplier_name: string;
  supplier_code: string;
  provider_code: string;
  model_code: string | null;
  billing_unit: string;
  currency: string;
  wholesale_cost_minor_units: number;
  contract_status: string;
  is_active: boolean;
};

type PaymentEvent = {
  id: number;
  event_type: string;
  tracker_token: string | null;
  order_reference: string | null;
  provider_state: string | null;
  payment_order_id: number | null;
  amount_minor_units: number | null;
  currency: string | null;
  processing_status: string;
  received_at: string;
};

type AIRequest = {
  id: number;
  user_id: number;
  provider: string;
  model: string;
  status: string;
  reservation_id: number | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  credits_charged: number;
  input_rate_minor_units: number;
  output_rate_minor_units: number;
  error_code: string | null;
  created_at: string;
};

function ReconciliationForm({
  item,
  onReconcile,
  onRelease,
}: {
  item: AIRequest;
  onReconcile: (id: number, prompt: number, completion: number, evidence: string) => Promise<void>;
  onRelease: (id: number, evidence: string) => Promise<void>;
}) {
  const [prompt, setPrompt] = useState(item.prompt_tokens?.toString() || "");
  const [completion, setCompletion] = useState(item.completion_tokens?.toString() || "");
  const [evidence, setEvidence] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const promptCount = Number(prompt);
    const completionCount = Number(completion);
    if (!Number.isInteger(promptCount) || promptCount < 0 ||
        !Number.isInteger(completionCount) || completionCount < 0 || evidence.trim().length < 8) return;
    setBusy(true);
    try {
      await onReconcile(item.id, promptCount, completionCount, evidence.trim());
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="admin-reconcile-form" onSubmit={submit}>
      <label>Verified prompt tokens
        <input type="number" min="0" required value={prompt} onChange={(event) => setPrompt(event.target.value)} />
      </label>
      <label>Verified completion tokens
        <input type="number" min="0" required value={completion} onChange={(event) => setCompletion(event.target.value)} />
      </label>
      <label>Evidence reference
        <input required minLength={8} maxLength={255} value={evidence} onChange={(event) => setEvidence(event.target.value)} placeholder="Provider usage log / ticket reference" />
      </label>
      <button className="account-button" type="submit" disabled={busy}>
        {busy ? "Settling…" : "Verify and settle hold"}
      </button>
      <button className="account-button secondary" type="button" disabled={busy || evidence.trim().length < 8} onClick={async () => { setBusy(true); try { await onRelease(item.id, evidence.trim()); } finally { setBusy(false); } }}>
        Release full hold (platform absorbs cost)
      </button>
    </form>
  );
}

export default function AdminConsole() {
  const [isAdmin, setIsAdmin] = useState(false);
  const [checkingRole, setCheckingRole] = useState(true);
  const [offers, setOffers] = useState<SupplierOffer[]>([]);
  const [requests, setRequests] = useState<AIRequest[]>([]);
  const [paymentEvents, setPaymentEvents] = useState<PaymentEvent[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [supplierName, setSupplierName] = useState("");
  const [supplierCode, setSupplierCode] = useState("");
  const [provider, setProvider] = useState<"openai" | "mistral">("openai");
  const [model, setModel] = useState("");
  const [billingUnit, setBillingUnit] = useState<"per_1k_input_tokens" | "per_1k_output_tokens">("per_1k_input_tokens");
  const [wholesaleCost, setWholesaleCost] = useState("");
  const [contractVerified, setContractVerified] = useState(false);

  const refresh = useCallback(async () => {
    const [offerResponse, requestResponse, paymentResponse] = await Promise.all([
      fetch("/api/admin/supplier-offers", { cache: "no-store" }),
      fetch("/api/admin/ai-requests", { cache: "no-store" }),
      fetch("/api/admin/payment-events", { cache: "no-store" }),
    ]);
    const [offerData, requestData, paymentData] = await Promise.all([
      offerResponse.json().catch(() => ({})),
      requestResponse.json().catch(() => ({})),
      paymentResponse.json().catch(() => ({})),
    ]);
    if (!offerResponse.ok || !requestResponse.ok || !paymentResponse.ok) {
      throw new Error(offerData.detail || requestData.detail || paymentData.detail || "Could not load admin data");
    }
    setOffers(offerData as SupplierOffer[]);
    setRequests(requestData as AIRequest[]);
    setPaymentEvents(paymentData as PaymentEvent[]);
  }, []);

  useEffect(() => {
    let active = true;
    fetch("/api/account", { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) return null;
        return await response.json();
      })
      .then(async (account) => {
        if (!active || account?.user?.role !== "admin") return;
        setIsAdmin(true);
        try { await refresh(); }
        catch (cause) {
          if (active) setError(cause instanceof Error ? cause.message : "Admin data unavailable");
        }
      })
      .catch(() => {
        if (active) setError("Could not verify administrator session");
      })
      .finally(() => {
        if (active) setCheckingRole(false);
      });
    return () => { active = false; };
  }, [refresh]);

  useEffect(() => {
    let active = true;
    const refreshRole = async () => {
      try {
        const response = await fetch("/api/account", { cache: "no-store" });
        if (!response.ok) {
          if (active) setIsAdmin(false);
          return;
        }
        const account = await response.json();
        const allowed = account?.user?.role === "admin";
        if (!active) return;
        setIsAdmin(allowed);
        if (allowed) {
          try { await refresh(); }
          catch (cause) {
            if (active) setError(cause instanceof Error ? cause.message : "Admin data unavailable");
          }
        }
      } catch {
        if (active) setIsAdmin(false);
      }
    };
    window.addEventListener("aiph:auth-changed", refreshRole);
    return () => {
      active = false;
      window.removeEventListener("aiph:auth-changed", refreshRole);
    };
  }, [refresh]);

  async function createOffer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cost = Number(wholesaleCost);
    if (!Number.isSafeInteger(cost) || cost <= 0 || !model.trim() || !contractVerified) {
      setError("Enter a valid model id, positive whole-paisa rate, and confirm verified supplier resale rights.");
      return;
    }
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const response = await fetch("/api/admin/supplier-offers", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          supplier_name: supplierName,
          supplier_code: supplierCode,
          service_type: "ai_api",
          provider_code: provider,
          model_code: model.trim(),
          billing_unit: billingUnit,
          currency: "PKR",
          wholesale_cost_minor_units: cost,
          contract_status: "verified",
          is_active: true,
        }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail || "Could not create supplier rate");
      setNotice("Supplier rate saved. Add the matching input or output rate before the model appears in customer chat.");
      setWholesaleCost("");
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Supplier offer failed");
    } finally {
      setBusy(false);
    }
  }

  async function releaseHold(id: number, evidence: string) {
    setError("");
    setNotice("");
    try {
      const response = await fetch("/api/admin/ai-requests/" + id + "/release", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ evidence_reference: evidence }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) {
        setError(result.detail || "Hold release failed");
        return;
      }
      setNotice("AI request #" + id + " hold released. The platform absorbs any provider cost for this request.");
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Hold release service unavailable");
    }
  }

  async function reconcile(id: number, promptTokens: number, completionTokens: number, evidence: string) {
    setError("");
    setNotice("");
    try {
      const response = await fetch("/api/admin/ai-requests/" + id + "/reconcile", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          prompt_tokens: promptTokens,
          completion_tokens: completionTokens,
          evidence_reference: evidence,
        }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) {
        setError(result.detail || "Reconciliation failed");
        return;
      }
      setNotice("AI request #" + id + " reconciled. Credits have been settled using the stored rate snapshot.");
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Reconciliation service unavailable");
    }
  }

  if (checkingRole || !isAdmin) return null;

  return (
    <section className="admin-console" id="admin">
      <div className="admin-heading">
        <div><span className="eyebrow">CONTROL PLANE</span><h2>Administrator Console</h2></div>
        <span className="chat-mode">Admin access</span>
      </div>
      <p className="admin-disclaimer">
        Supplier verification and reconciliation evidence are administrator attestations. Confirm signed resale terms and provider usage records outside this interface before activating rates or settling held credits.
      </p>
      {error ? <p className="chat-error" role="alert">{error}</p> : null}
      {notice ? <p className="admin-notice" role="status">{notice}</p> : null}

      <div className="admin-grid">
        <section className="admin-section">
          <h3>Register a supplier token rate</h3>
          <p>Add one input and one output rate for the same supplier, provider and model. Costs are entered in PKR paisa per 1,000 tokens.</p>
          <form className="admin-offer-form" onSubmit={createOffer}>
            <label>Supplier name<input required minLength={2} maxLength={160} value={supplierName} onChange={(event) => setSupplierName(event.target.value)} /></label>
            <label>Supplier code<input required minLength={2} maxLength={80} pattern="[A-Za-z0-9_-]+" value={supplierCode} onChange={(event) => setSupplierCode(event.target.value)} /></label>
            <label>Provider<select value={provider} onChange={(event) => setProvider(event.target.value as "openai" | "mistral")}><option value="openai">OpenAI</option><option value="mistral">Mistral</option></select></label>
            <label>Exact model id<input required minLength={1} maxLength={120} value={model} onChange={(event) => setModel(event.target.value)} placeholder="Approved model id" /></label>
            <label>Billing unit<select value={billingUnit} onChange={(event) => setBillingUnit(event.target.value as "per_1k_input_tokens" | "per_1k_output_tokens")}><option value="per_1k_input_tokens">Input tokens / 1k</option><option value="per_1k_output_tokens">Output tokens / 1k</option></select></label>
            <label>Wholesale cost (paisa)<input type="number" min="1" step="1" required value={wholesaleCost} onChange={(event) => setWholesaleCost(event.target.value)} /></label>
            <label className="admin-verify-check"><input type="checkbox" required checked={contractVerified} onChange={(event) => setContractVerified(event.target.checked)} /> I have independently verified the supplier contract and resale rights.</label>
            <button className="account-button" type="submit" disabled={busy}>{busy ? "Saving…" : "Save supplier rate"}</button>
          </form>
          <div className="admin-offer-list">
            <h4>Registered offers ({offers.length})</h4>
            {offers.slice(0, 12).map((offer) => (
              <div className="admin-offer-row" key={offer.id}>
                <span><strong>{offer.provider_code} · {offer.model_code || "No model"}</strong><small>{offer.supplier_name} · {offer.billing_unit.replaceAll("_", " ")}</small></span>
                <span><strong>{offer.wholesale_cost_minor_units.toLocaleString()} paisa</strong><small>{offer.contract_status} · {offer.is_active ? "active" : "inactive"}</small></span>
              </div>
            ))}
            {offers.length === 0 ? <small className="account-muted">No supplier rates registered.</small> : null}
          </div>
        </section>

        <section className="admin-section">
          <h3>AI usage reconciliation</h3>
          <p>Requests with missing or over-limit provider usage keep customer credits reserved until verified usage is settled.</p>
          {requests.map((item) => (
            <article className="admin-request-card" key={item.id}>
              <div className="admin-request-meta">
                <strong>Request #{item.id} · User #{item.user_id}</strong>
                <small>{item.provider} · {item.model} · {item.error_code || item.status}</small>
              </div>
              <ReconciliationForm item={item} onReconcile={reconcile} onRelease={releaseHold} />
            </article>
          ))}
          {requests.length === 0 ? <div className="chat-empty">No AI requests are waiting for reconciliation.</div> : null}
        </section>
      </div>

      <section className="admin-section admin-payment-events">
        <h3>Safepay webhook event inbox</h3>
        <p>Signed provider events are retained for audit. A browser return is not payment confirmation; only the verified webhook can settle a top-up.</p>
        {paymentEvents.map((event) => (
          <article className="admin-payment-row" key={event.id}>
            <div>
              <strong>{event.event_type}</strong>
              <small>Order: {event.order_reference || "unmatched"} · Tracker: {event.tracker_token || "not supplied"}</small>
              <small>{event.provider_state || "No provider state"} · {new Date(event.received_at).toLocaleString()}</small>
            </div>
            <div>
              <strong>{event.amount_minor_units == null ? "—" : event.amount_minor_units.toLocaleString() + " " + (event.currency || "")}</strong>
              <small>{event.processing_status}</small>
            </div>
          </article>
        ))}
        {paymentEvents.length === 0 ? <div className="chat-empty">No Safepay webhook events received.</div> : null}
      </section>
    </section>
  );
}
