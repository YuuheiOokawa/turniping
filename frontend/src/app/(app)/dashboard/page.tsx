"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { MarketStatusBanner } from "@/components/dashboard/MarketStatusBanner";
import { InstrumentRow } from "@/components/dashboard/InstrumentRow";

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const [newCode, setNewCode] = useState("");

  const { data: instruments, isLoading } = useQuery({
    queryKey: ["instruments"],
    queryFn: api.instruments,
  });

  const addMutation = useMutation({
    mutationFn: (code: string) => api.addWatchlist(code),
    onSuccess: () => {
      setNewCode("");
      queryClient.invalidateQueries({ queryKey: ["instruments"] });
    },
  });

  const removeMutation = useMutation({
    mutationFn: (code: string) => api.removeWatchlist(code),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["instruments"] }),
  });

  return (
    <div className="flex flex-col gap-4">
      <MarketStatusBanner />

      <Card>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">ウォッチリスト</h2>
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              if (newCode.trim()) addMutation.mutate(newCode.trim());
            }}
          >
            <input
              value={newCode}
              onChange={(e) => setNewCode(e.target.value)}
              placeholder="例: 9432.T"
              className="rounded border border-neutral-300 px-2 py-1 text-sm dark:border-neutral-700 dark:bg-neutral-900"
            />
            <button
              type="submit"
              className="rounded bg-neutral-900 px-3 py-1 text-sm text-white dark:bg-neutral-100 dark:text-neutral-900"
            >
              追加
            </button>
          </form>
        </div>

        {isLoading && <p className="text-sm text-neutral-500">読み込み中...</p>}
        {addMutation.isError && (
          <p className="mb-2 text-sm text-up">{(addMutation.error as Error).message}</p>
        )}

        {instruments && (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-neutral-500">
                <th className="pb-2 font-normal">銘柄</th>
                <th className="pb-2 text-right font-normal">現在値</th>
                <th className="pb-2 text-right font-normal">前日比</th>
                <th className="pb-2 text-right font-normal">予想</th>
                <th className="pb-2 text-right font-normal"></th>
              </tr>
            </thead>
            <tbody>
              {instruments.map((instrument) => (
                <InstrumentRow
                  key={instrument.code}
                  instrument={instrument}
                  onRemove={(code) => removeMutation.mutate(code)}
                />
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
