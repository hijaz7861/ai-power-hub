import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const backend = process.env.API_BASE_URL || "http://127.0.0.1:8000";

export async function GET() {
  const store = await cookies();
  const token = store.get("aiph_session")?.value;
  if (!token) {
    return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
  }

  const headers = { Authorization: "Bearer " + token };
  try {
    const [userResponse, balanceResponse, ledgerResponse] = await Promise.all([
      fetch(backend + "/api/v1/auth/me", { headers, cache: "no-store" }),
      fetch(backend + "/api/v1/credits/balance", { headers, cache: "no-store" }),
      fetch(backend + "/api/v1/credits/ledger?limit=10", { headers, cache: "no-store" }),
    ]);

    if ([userResponse, balanceResponse, ledgerResponse].some((response) => response.status === 401)) {
      store.delete("aiph_session");
      return NextResponse.json({ detail: "Session expired" }, { status: 401 });
    }
    if (!userResponse.ok || !balanceResponse.ok || !ledgerResponse.ok) {
      return NextResponse.json({ detail: "Account data unavailable" }, { status: 502 });
    }

    const [user, balance, ledger] = await Promise.all([
      userResponse.json(),
      balanceResponse.json(),
      ledgerResponse.json(),
    ]);
    return NextResponse.json({ user, balance, ledger });
  } catch {
    return NextResponse.json({ detail: "Account service unavailable" }, { status: 503 });
  }
}
