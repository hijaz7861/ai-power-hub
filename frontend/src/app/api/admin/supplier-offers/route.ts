import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

const backend = process.env.API_BASE_URL || "http://127.0.0.1:8000";

async function adminRequest(request: NextRequest, method: "GET" | "POST") {
  const store = await cookies();
  const token = store.get("aiph_session")?.value;
  if (!token) return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
  let body: unknown;
  if (method === "POST") {
    try { body = await request.json(); }
    catch { return NextResponse.json({ detail: "Invalid JSON body" }, { status: 400 }); }
  }
  try {
    const upstream = await fetch(backend + "/api/v1/admin/supplier-offers", {
      method,
      headers: {
        Authorization: "Bearer " + token,
        ...(method === "POST" ? { "content-type": "application/json" } : {}),
      },
      ...(method === "POST" ? { body: JSON.stringify(body) } : {}),
      cache: "no-store",
    });
    const result = await upstream.json().catch(() => ({}));
    return NextResponse.json(result, { status: upstream.status });
  } catch {
    return NextResponse.json({ detail: "Admin service unavailable" }, { status: 503 });
  }
}

export async function GET(request: NextRequest) { return adminRequest(request, "GET"); }
export async function POST(request: NextRequest) { return adminRequest(request, "POST"); }
