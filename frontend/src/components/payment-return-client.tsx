"use client";

import { useCallback, useEffect, useState } from "react";

type PaymentStatus = {
  reference: string;
  amount_pkr: number;
  amount_minor_units: number;
  currency: string;
  status: string;
  paid_at: string | null;
};

export default function PaymentReturnClient({ reference }: { reference: string }) {
  const [payment, setPayment] = useState<PaymentStatus | null>(null);
  const [error, setError] = useState("");
  const [checking, setChecking] = useState(true);

  const refresh = useCallback(async () => {
    if (!reference) {
      setError("Payment reference is missing.");
      setChecking(false);
      return false;
    }
    try {
      const response = await fetch("/api/payments/topups/" + encodeURIComponent(reference), { cache: "no-store" });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.detail || "Could not retrieve payment status");
      setPayment(result as PaymentStatus);
      setError("");
      return result.status === "succeeded";
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Payment status unavailable");
      return false;
    } finally {
      setChecking(false);
    }
  }, [reference]);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setInterval> | undefined;
    const run = async () => {
      const complete = await refresh();
      if (complete && timer) clearInterval(timer);
    };
    run();
    timer = setInterval(() => {
      if (active) run();
    }, 5000);
    return () => {
      active = false;
      if (timer) clearInterval(timer);
    };
  }, [refresh]);

  return (
    <main className="payment-page">
      <section className="payment-card">
        <span className="eyebrow">AI POWER HUB · PAYMENT STATUS</span>
        <h1>{payment?.status === "succeeded" ? "Payment confirmed" : "Verifying your payment"}</h1>
        {payment ? <p>Order {payment.reference} · PKR {payment.amount_pkr.toLocaleString()}</p> : null}
        {payment?.status === "succeeded" ? (
          <div className="payment-success">Your top-up has been verified. {payment.amount_minor_units.toLocaleString()} credits were added to your account.</div>
        ) : (
          <div className="payment-pending">
            {checking ? "Checking the payment record…" : "The checkout redirect is not proof of payment. We are waiting for Safepay’s signed confirmation webhook."}
            <small>Keep this page open. Status refreshes automatically.</small>
          </div>
        )}
        {error ? <p className="payment-error">{error}</p> : null}
        <a className="primary-link" href="/">Return to AI Power Hub</a>
      </section>
    </main>
  );
}
