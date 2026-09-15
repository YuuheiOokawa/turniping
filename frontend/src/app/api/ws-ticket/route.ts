import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";

export async function POST() {
  const response = await fetch(`${BACKEND_URL}/api/v1/ws-ticket`, {
    method: "POST",
    headers: { Authorization: `Bearer ${process.env.BACKEND_API_TOKEN ?? ""}` },
    cache: "no-store",
  });
  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}
