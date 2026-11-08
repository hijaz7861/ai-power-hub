import { cookies } from "next/headers";
import { NextResponse } from "next/server";

export async function POST() {
  const store = await cookies();
  store.delete("aiph_session");
  return NextResponse.json({ ok: true });
}
