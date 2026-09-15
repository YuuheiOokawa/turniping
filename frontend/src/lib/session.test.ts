import { describe, expect, it } from "vitest";
import { createSessionToken, verifySessionToken } from "./session";

describe("session token", () => {
  it("round-trips a valid token", async () => {
    const token = await createSessionToken();
    expect(await verifySessionToken(token)).toBe(true);
  });

  it("rejects a tampered token", async () => {
    expect(await verifySessionToken("authenticated.deadbeef")).toBe(false);
  });

  it("rejects an undefined token", async () => {
    expect(await verifySessionToken(undefined)).toBe(false);
  });
});
