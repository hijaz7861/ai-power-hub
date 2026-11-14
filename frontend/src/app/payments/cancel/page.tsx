export default async function PaymentCancelPage({
  searchParams,
}: {
  searchParams: Promise<{ reference?: string }>;
}) {
  const params = await searchParams;
  return (
    <main className="payment-page">
      <section className="payment-card">
        <span className="eyebrow">AI POWER HUB · CHECKOUT</span>
        <h1>Checkout cancelled</h1>
        <p>Your payment has not been confirmed. No credits have been added.</p>
        {params.reference ? <a className="primary-link" href={"/payments/return?reference=" + encodeURIComponent(params.reference)}>Check payment status</a> : null}
        <a className="secondary-link" href="/">Return to AI Power Hub</a>
      </section>
    </main>
  );
}
