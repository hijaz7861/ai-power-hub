import { NextRequest, NextResponse } from "next/server";

const backend = process.env.API_BASE_URL || "http://127.0.0.1:8000";

export async function POST(request: NextRequest) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: "Invalid JSON body" }, { status: 400 });
  }

  try {
    const upstream = await fetch(backend + "/api/v1/auth/register", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });
    const result = await upstream.json().catch(() => ({}));
    if (!upstream.ok) {
      return NextResponse.json(
        { detail: result.detail || "Registration failed" },
        { status: upstream.status },
      );
    }
    return NextResponse.json({ id: result.id, email: result.email }, { status: 201 });
  } catch {
    return NextResponse.json({ detail: "Authentication service unavailable" }, { status: 503 });
  }
}
