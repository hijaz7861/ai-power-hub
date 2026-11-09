import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backend = process.env.API_BASE_URL || "http://127.0.0.1:8000";

export async function GET() {
  const store = await cookies();
  const token = store.get("aiph_session")?.value;
  if (!token) return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
  try {
    const upstream = await fetch(backend + "/api/v1/admin/payment-events?limit=50", {
      headers: { Authorization: "Bearer " + token },
      cache: "no-store",
    });
    const result = await upstream.json().catch(() => ({}));
    return NextResponse.json(result, { status: upstream.status });
  } catch {
    return NextResponse.json({ detail: "Payment event service unavailable" }, { status: 503 });
  }
}
