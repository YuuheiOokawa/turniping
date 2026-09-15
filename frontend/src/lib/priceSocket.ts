export type PriceTick = { code: string; price: number; ts: string };

export function connectPriceSocket(
  codes: string[],
  onTick: (tick: PriceTick) => void
): () => void {
  let socket: WebSocket | null = null;
  let closed = false;

  (async () => {
    const res = await fetch("/api/ws-ticket", { method: "POST" });
    if (!res.ok || closed) return;
    const { ticket } = await res.json();

    const wsUrl = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";
    const url = `${wsUrl}/ws/prices?ticket=${encodeURIComponent(ticket)}&codes=${encodeURIComponent(
      codes.join(",")
    )}`;
    if (closed) return;
    socket = new WebSocket(url);
    socket.onmessage = (event) => {
      try {
        onTick(JSON.parse(event.data));
      } catch {
        // ignore malformed frames
      }
    };
  })();

  return () => {
    closed = true;
    socket?.close();
  };
}
