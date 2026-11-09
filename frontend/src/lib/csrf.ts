import { NextRequest, NextResponse } from "next/server";

/**
 * Reject cross-origin browser mutations at the cookie-authenticated BFF.
 * Configure APP_ORIGIN to the exact public origin in production.
 */
export function rejectCrossOriginMutation(request: NextRequest): NextResponse | null {
  let expectedOrigin: string;
  try {
    if (process.env.NODE_ENV === "production" && !process.env.APP_ORIGIN) {
      return NextResponse.json(
        { detail: "APP_ORIGIN must be configured before enabling production sessions" },
        { status: 503 },
      );
    }
    expectedOrigin = new URL(process.env.APP_ORIGIN || request.nextUrl.origin).origin;
  } catch {
    return NextResponse.json({ detail: "Invalid application origin configuration" }, { status: 503 });
  }

  const origin = request.headers.get("origin");
  if (origin) {
    try {
      if (new URL(origin).origin === expectedOrigin) return null;
    } catch {
      // Invalid Origin is rejected below.
    }
  } else if (request.headers.get("sec-fetch-site") === "same-origin") {
    return null;
  }

  return NextResponse.json({ detail: "Cross-origin request rejected" }, { status: 403 });
}
