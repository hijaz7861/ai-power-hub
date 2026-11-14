import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backend = process.env.API_BASE_URL || "http://127.0.0.1:8000";

export async function GET() {
  const store = await cookies();
  const token = store.get("aiph_session")?.value;
  if (!token) return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
  try {
    const upstream = await fetch(backend + "/api/v1/account/export", {
      headers: { Authorization: "Bearer " + token },
      cache: "no-store",
    });
    const body = await upstream.text();
    return new NextResponse(body, {
      status: upstream.status,
      headers: {
        "content-type": upstream.headers.get("content-type") || "application/json",
        "content-disposition": upstream.headers.get("content-disposition") || 'attachment; filename="ai-power-hub-account-export.json"',
        "cache-control": "no-store",
      },
    });
  } catch {
    return NextResponse.json({ detail: "Account export service unavailable" }, { status: 503 });
  }
}
