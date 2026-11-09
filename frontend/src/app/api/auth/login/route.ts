import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { rejectCrossOriginMutation } from "../../../../lib/csrf";
import { forwardedClientIpHeader } from "../../../../lib/forwarded-client-ip";

const backend = process.env.API_BASE_URL || "http://127.0.0.1:8000";

export async function POST(request: NextRequest) {
  const rejected = rejectCrossOriginMutation(request);
  if (rejected) return rejected;
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: "Invalid JSON body" }, { status: 400 });
  }

  let upstream: Response;
  try {
    upstream = await fetch(backend + "/api/v1/auth/login", {
      method: "POST",
      headers: { "content-type": "application/json", ...forwardedClientIpHeader(request) },
      body: JSON.stringify(body),
      cache: "no-store",
    });
  } catch {
    return NextResponse.json({ detail: "Authentication service unavailable" }, { status: 503 });
  }

  const result = await upstream.json().catch(() => ({}));
  if (!upstream.ok) {
    return NextResponse.json(
      { detail: result.detail || "Login failed" },
      { status: upstream.status },
    );
  }

  if (typeof result.access_token !== "string") {
    return NextResponse.json({ detail: "Invalid authentication response" }, { status: 502 });
  }

  const configuredMinutes = Number.parseInt(process.env.ACCESS_TOKEN_MINUTES || "30", 10);
  const maxAge = Number.isFinite(configuredMinutes) ? Math.max(1, Math.min(configuredMinutes, 1440)) * 60 : 1800;
  const store = await cookies();
  store.set("aiph_session", result.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict",
    path: "/",
    maxAge,
  });

  return NextResponse.json({ ok: true });
}
