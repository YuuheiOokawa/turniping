"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api, Instrument } from "@/lib/api";
import { DirectionBadge } from "@/components/prediction/DirectionBadge";
import clsx from "clsx";

export function InstrumentRow({
  instrument,
  onRemove,
}: {
  instrument: Instrument;
  onRemove: (code: string) => void;
}) {
  const { data: prediction } = useQuery({
    queryKey: ["prediction", instrument.code],
    queryFn: () => api.latestPrediction(instrument.code),
  });

  const changePositive = (instrument.change_pct ?? 0) >= 0;

  return (
    <tr className="border-b border-neutral-100 last:border-0 dark:border-neutral-800">
      <td className="py-3">
        <Link href={`/instruments/${instrument.code}`} className="font-medium hover:underline">
          {instrument.name}
        </Link>
        <div className="text-xs text-neutral-500">{instrument.code}</div>
      </td>
      <td className="py-3 text-right tabular-nums">
        {instrument.last_price !== null
          ? instrument.last_price.toLocaleString(undefined, { maximumFractionDigits: 1 })
          : "-"}
      </td>
      <td
        className={clsx(
          "py-3 text-right tabular-nums",
          changePositive ? "text-up" : "text-down"
        )}
      >
        {instrument.change_pct !== null ? `${changePositive ? "+" : ""}${instrument.change_pct.toFixed(2)}%` : "-"}
      </td>
      <td className="py-3 text-right">
        {prediction ? (
          <DirectionBadge direction={prediction.direction} confidence={prediction.confidence} />
        ) : (
          <span className="text-xs text-neutral-400">予想なし</span>
        )}
      </td>
      <td className="py-3 text-right">
        <button
          onClick={() => onRemove(instrument.code)}
          className="text-xs text-neutral-400 hover:text-up"
        >
          削除
        </button>
      </td>
    </tr>
  );
}
