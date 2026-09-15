// Edge Runtime (middleware) では Node の `crypto` モジュールが使えないため、
// Web Crypto API (globalThis.crypto.subtle) だけで完結させる。

export const SESSION_COOKIE_NAME = "turniping_session";
const SESSION_VALUE = "authenticated";

async function sign(secret: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const signature = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(SESSION_VALUE));
  return Array.from(new Uint8Array(signature))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export async function createSessionToken(): Promise<string> {
  const secret = process.env.SESSION_SECRET ?? "dev-local-session-secret";
  return `${SESSION_VALUE}.${await sign(secret)}`;
}

export async function verifySessionToken(token: string | undefined): Promise<boolean> {
  if (!token) return false;
  const [value, signature] = token.split(".");
  if (value !== SESSION_VALUE || !signature) return false;

  const secret = process.env.SESSION_SECRET ?? "dev-local-session-secret";
  const expected = await sign(secret);
  if (signature.length !== expected.length) return false;

  // タイミング攻撃を避けるための定数時間比較
  let diff = 0;
  for (let i = 0; i < expected.length; i++) {
    diff |= signature.charCodeAt(i) ^ expected.charCodeAt(i);
  }
  return diff === 0;
}

export function isAuthGateEnabled(): boolean {
  return process.env.APP_ENV !== "development";
}
