"use client";

import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";

export default function SystemPage() {
  const router = useRouter();
  const { data: status } = useQuery({ queryKey: ["system-status"], queryFn: api.systemStatus });

  async function handleLogout() {
    await fetch("/api/session-logout", { method: "POST" });
    router.push("/login");
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">システム状態</h1>
      <Card>
        <dl className="grid grid-cols-2 gap-2 text-sm">
          <dt className="text-neutral-500">現在時刻(JST)</dt>
          <dd>{status?.now_jst ?? "-"}</dd>
          <dt className="text-neutral-500">市場</dt>
          <dd>{status?.market_open ? "開場中" : "閉場中"}</dd>
          <dt className="text-neutral-500">次回開場</dt>
          <dd>{status?.next_open_jst ?? "-"}</dd>
        </dl>
      </Card>
      <button
        onClick={handleLogout}
        className="w-fit rounded border border-neutral-300 px-3 py-1 text-sm dark:border-neutral-700"
      >
        ログアウト
      </button>
    </div>
  );
}
