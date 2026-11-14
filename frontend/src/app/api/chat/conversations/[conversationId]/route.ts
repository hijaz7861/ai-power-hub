import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { rejectCrossOriginMutation } from "../../../../../lib/csrf";

const backend = process.env.API_BASE_URL || "http://127.0.0.1:8000";

export async function GET(
  _request: Request,
  context: { params: Promise<{ conversationId: string }> },
) {
  const store = await cookies();
  const token = store.get("aiph_session")?.value;
  if (!token) return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
  const { conversationId } = await context.params;
  if (!/^\d+$/.test(conversationId)) {
    return NextResponse.json({ detail: "Invalid conversation id" }, { status: 400 });
  }
  try {
    const upstream = await fetch(
      backend + "/api/v1/chat/conversations/" + conversationId,
      { headers: { Authorization: "Bearer " + token }, cache: "no-store" },
    );
    const result = await upstream.json().catch(() => ({}));
    return NextResponse.json(result, { status: upstream.status });
  } catch {
    return NextResponse.json({ detail: "Conversation service unavailable" }, { status: 503 });
  }
}


export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ conversationId: string }> },
) {
  const rejected = rejectCrossOriginMutation(request);
  if (rejected) return rejected;
  const store = await cookies();
  const token = store.get("aiph_session")?.value;
  if (!token) return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
  const { conversationId } = await context.params;
  if (!/^\d+$/.test(conversationId)) {
    return NextResponse.json({ detail: "Invalid conversation id" }, { status: 400 });
  }
  try {
    const upstream = await fetch(
      backend + "/api/v1/chat/conversations/" + conversationId,
      {
        method: "DELETE",
        headers: { Authorization: "Bearer " + token },
        cache: "no-store",
      },
    );
    if (upstream.status === 204) return new NextResponse(null, { status: 204 });
    const result = await upstream.json().catch(() => ({}));
    return NextResponse.json(result, { status: upstream.status });
  } catch {
    return NextResponse.json({ detail: "Conversation service unavailable" }, { status: 503 });
  }
}
