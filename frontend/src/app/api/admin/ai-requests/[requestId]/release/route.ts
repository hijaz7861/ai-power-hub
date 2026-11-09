import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const backend = process.env.API_BASE_URL || "http://127.0.0.1:8000";

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ requestId: string }> },
) {
  const store = await cookies();
  const token = store.get("aiph_session")?.value;
  if (!token) return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
  const { requestId } = await context.params;
  if (!/^\d+$/.test(requestId)) {
    return NextResponse.json({ detail: "Invalid request id" }, { status: 400 });
  }
  let body: unknown;
  try { body = await request.json(); }
  catch { return NextResponse.json({ detail: "Invalid JSON body" }, { status: 400 }); }
  try {
    const upstream = await fetch(
      backend + "/api/v1/admin/ai-requests/" + requestId + "/release",
      {
        method: "POST",
        headers: {
          Authorization: "Bearer " + token,
          "content-type": "application/json",
        },
        body: JSON.stringify(body),
        cache: "no-store",
      },
    );
    const result = await upstream.json().catch(() => ({}));
    return NextResponse.json(result, { status: upstream.status });
  } catch {
    return NextResponse.json({ detail: "Admin release service unavailable" }, { status: 503 });
  }
}
