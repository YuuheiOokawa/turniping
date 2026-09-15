"use client";

import { useEffect, useRef } from "react";
import { createChart, ColorType } from "lightweight-charts";
import { Candle } from "@/lib/api";

export function CandleChart({ candles }: { candles: Candle[] }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      height: 320,
      layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: "#888" },
      grid: { vertLines: { color: "#eee" }, horzLines: { color: "#eee" } },
      timeScale: { timeVisible: true },
    });

    // 日本の慣習に合わせ陽線=赤、陰線=緑にする
    const series = chart.addCandlestickSeries({
      upColor: "#d1453b",
      downColor: "#22795e",
      borderVisible: false,
      wickUpColor: "#d1453b",
      wickDownColor: "#22795e",
    });

    series.setData(
      candles.map((c) => ({
        time: (new Date(c.ts).getTime() / 1000) as never,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }))
    );
    chart.timeScale().fitContent();

    const resize = () => chart.applyOptions({ width: containerRef.current?.clientWidth });
    resize();
    window.addEventListener("resize", resize);

    return () => {
      window.removeEventListener("resize", resize);
      chart.remove();
    };
  }, [candles]);

  return <div ref={containerRef} className="w-full" />;
}
