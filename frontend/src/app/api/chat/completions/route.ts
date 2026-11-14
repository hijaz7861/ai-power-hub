import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { rejectCrossOriginMutation } from "../../../../lib/csrf";
import { forwardedClientIpHeader } from "../../../../lib/forwarded-client-ip";

const backend = process.env.API_BASE_URL || "http://127.0.0.1:8000";

export async function POST(request: NextRequest) {
  const rejected = rejectCrossOriginMutation(request);
  if (rejected) return rejected;
  const store = await cookies();
  const token = store.get("aiph_session")?.value;
  if (!token) {
    return NextResponse.json({ detail: "Sign in before using AI chat" }, { status: 401 });
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: "Invalid JSON body" }, { status: 400 });
  }

  try {
    const upstream = await fetch(backend + "/api/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: "Bearer " + token,
        "content-type": "application/json",
        ...forwardedClientIpHeader(request),
      },
      body: JSON.stringify(body),
      cache: "no-store",
      signal: AbortSignal.timeout(40000),
    });
    const result = await upstream.json().catch(() => ({}));
    return NextResponse.json(result, { status: upstream.status });
  } catch {
    return NextResponse.json({ detail: "AI chat service unavailable" }, { status: 503 });
  }
}
