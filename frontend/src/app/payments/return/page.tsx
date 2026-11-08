import PaymentReturnClient from "../../../components/payment-return-client";

export default async function PaymentReturnPage({
  searchParams,
}: {
  searchParams: Promise<{ reference?: string }>;
}) {
  const params = await searchParams;
  return <PaymentReturnClient reference={params.reference || ""} />;
}
