import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { rejectCrossOriginMutation } from "../../../../lib/csrf";

export async function POST(request: NextRequest) {
  const rejected = rejectCrossOriginMutation(request);
  if (rejected) return rejected;
  const store = await cookies();
  store.delete("aiph_session");
  return NextResponse.json({ ok: true });
}
