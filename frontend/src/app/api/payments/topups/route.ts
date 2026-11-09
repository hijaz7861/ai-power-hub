import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { rejectCrossOriginMutation } from "../../../../lib/csrf";

const backend = process.env.API_BASE_URL || "http://127.0.0.1:8000";

export async function POST(request: NextRequest) {
  const rejected = rejectCrossOriginMutation(request);
  if (rejected) return rejected;
  const store = await cookies();
  const token = store.get("aiph_session")?.value;
  if (!token) return NextResponse.json({ detail: "Authentication required" }, { status: 401 });

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: "Invalid JSON body" }, { status: 400 });
  }

  try {
    const upstream = await fetch(backend + "/api/v1/payments/topups", {
      method: "POST",
      headers: {
        Authorization: "Bearer " + token,
        "content-type": "application/json",
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    const result = await upstream.json().catch(() => ({}));
    return NextResponse.json(result, { status: upstream.status });
  } catch {
    return NextResponse.json({ detail: "Payment service unavailable" }, { status: 503 });
  }
}
