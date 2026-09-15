import clsx from "clsx";
import { ArrowDown, ArrowUp } from "lucide-react";

export function DirectionBadge({
  direction,
  confidence,
}: {
  direction: "up" | "down";
  confidence: number;
}) {
  const isUp = direction === "up";
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-full px-2 py-1 text-sm font-medium",
        isUp ? "bg-red-100 text-up dark:bg-red-950" : "bg-emerald-100 text-down dark:bg-emerald-950"
      )}
    >
      {isUp ? <ArrowUp size={14} /> : <ArrowDown size={14} />}
      {isUp ? "上昇" : "下落"}予想 ({confidence.toFixed(0)}%)
    </span>
  );
}
