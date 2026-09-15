import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";

async function proxy(request: NextRequest, params: { path: string[] }) {
  const targetPath = params.path.join("/");
  const search = request.nextUrl.search;
  const url = `${BACKEND_URL}/api/v1/${targetPath}${search}`;

  const headers = new Headers();
  headers.set("Authorization", `Bearer ${process.env.BACKEND_API_TOKEN ?? ""}`);
  const contentType = request.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);

  const hasBody = !["GET", "HEAD", "DELETE"].includes(request.method);
  const body = hasBody ? await request.text() : undefined;

  const response = await fetch(url, {
    method: request.method,
    headers,
    body,
    cache: "no-store",
  });

  const responseBody = await response.text();
  return new NextResponse(responseBody, {
    status: response.status,
    headers: { "content-type": response.headers.get("content-type") ?? "application/json" },
  });
}

export async function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, await context.params);
}
export async function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, await context.params);
}
export async function PUT(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, await context.params);
}
export async function DELETE(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, await context.params);
}
