"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { format } from "date-fns";

export function MarketStatusBanner() {
  const { data } = useQuery({ queryKey: ["system-status"], queryFn: api.systemStatus });

  if (!data) return null;

  return (
    <div
      className={
        data.market_open
          ? "rounded-md bg-red-50 px-4 py-2 text-sm text-up dark:bg-red-950/40"
          : "rounded-md bg-neutral-100 px-4 py-2 text-sm text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300"
      }
    >
      {data.market_open
        ? "東証は現在取引時間中です"
        : `市場は閉まっています。次回開場: ${
            data.next_open_jst ? format(new Date(data.next_open_jst), "MM/dd HH:mm") : "-"
          }`}
    </div>
  );
}
