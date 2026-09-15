import { NextRequest, NextResponse } from "next/server";
import { SESSION_COOKIE_NAME, isAuthGateEnabled, verifySessionToken } from "@/lib/session";

export async function middleware(request: NextRequest) {
  if (!isAuthGateEnabled()) {
    return NextResponse.next();
  }

  const token = request.cookies.get(SESSION_COOKIE_NAME)?.value;
  if (await verifySessionToken(token)) {
    return NextResponse.next();
  }

  const loginUrl = new URL("/login", request.url);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ["/((?!login|api/session-login|_next/static|_next/image|favicon.ico).*)"],
};
