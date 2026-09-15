import { NextRequest, NextResponse } from "next/server";
import { SESSION_COOKIE_NAME, createSessionToken } from "@/lib/session";

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => null);
  const token = body?.token as string | undefined;

  if (!token || token !== process.env.APP_API_TOKEN) {
    return NextResponse.json({ error: "invalid token" }, { status: 401 });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set(SESSION_COOKIE_NAME, await createSessionToken(), {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  });
  return response;
}
