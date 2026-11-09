import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const backend = process.env.API_BASE_URL || "http://127.0.0.1:8000";

export async function GET(request: NextRequest) {
  const requestStatus = request.nextUrl.searchParams.get("request_status") || "reconciliation_required";
  if (!["reconciliation_required", "processing"].includes(requestStatus)) {
    return NextResponse.json({ detail: "Unsupported AI request status" }, { status: 400 });
  }
  const store = await cookies();
  const token = store.get("aiph_session")?.value;
  if (!token) return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
  try {
    const upstream = await fetch(
      backend + "/api/v1/admin/ai-requests?request_status=" + requestStatus + "&limit=50",
      { headers: { Authorization: "Bearer " + token }, cache: "no-store" },
    );
    const result = await upstream.json().catch(() => ({}));
    return NextResponse.json(result, { status: upstream.status });
  } catch {
    return NextResponse.json({ detail: "Admin service unavailable" }, { status: 503 });
  }
}
