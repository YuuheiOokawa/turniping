"use client";

import { useEffect, useRef } from "react";
import { createChart, ColorType } from "lightweight-charts";
import { AiValuationPoint } from "@/lib/api";

export function EquityChart({ points, startingCash }: { points: AiValuationPoint[]; startingCash: number }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      height: 260,
      layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: "#888" },
      grid: { vertLines: { color: "#eee" }, horzLines: { color: "#eee" } },
      timeScale: { timeVisible: true },
    });

    const series = chart.addLineSeries({ color: "#2563eb", lineWidth: 2 });
    series.setData(
      points.map((p) => ({
        time: (new Date(p.ts).getTime() / 1000) as never,
        value: p.total_value_jpy,
      }))
    );

    const baseline = chart.addLineSeries({ color: "#999", lineWidth: 1, lineStyle: 2 });
    if (points.length > 0) {
      baseline.setData([
        { time: (new Date(points[0].ts).getTime() / 1000) as never, value: startingCash },
        { time: (new Date(points[points.length - 1].ts).getTime() / 1000) as never, value: startingCash },
      ]);
    }

    chart.timeScale().fitContent();

    const resize = () => chart.applyOptions({ width: containerRef.current?.clientWidth });
    resize();
    window.addEventListener("resize", resize);

    return () => {
      window.removeEventListener("resize", resize);
      chart.remove();
    };
  }, [points, startingCash]);

  return <div ref={containerRef} className="w-full" />;
}
