import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backend = process.env.API_BASE_URL || "http://127.0.0.1:8000";

export async function GET(
  _request: Request,
  context: { params: Promise<{ reference: string }> },
) {
  const store = await cookies();
  const token = store.get("aiph_session")?.value;
  if (!token) return NextResponse.json({ detail: "Authentication required" }, { status: 401 });

  const { reference } = await context.params;
  if (!/^[a-f0-9]{32}$/.test(reference)) {
    return NextResponse.json({ detail: "Invalid payment reference" }, { status: 400 });
  }

  try {
    const upstream = await fetch(
      backend + "/api/v1/payments/topups/" + encodeURIComponent(reference),
      {
        headers: { Authorization: "Bearer " + token },
        cache: "no-store",
      },
    );
    const result = await upstream.json().catch(() => ({}));
    return NextResponse.json(result, { status: upstream.status });
  } catch {
    return NextResponse.json({ detail: "Payment status unavailable" }, { status: 503 });
  }
}
