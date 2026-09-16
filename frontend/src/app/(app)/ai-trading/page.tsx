"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { EquityChart } from "@/components/chart/EquityChart";
import { format } from "date-fns";
import clsx from "clsx";

function formatJpy(value: number): string {
  return `¥${Math.round(value).toLocaleString()}`;
}

export default function AiTradingPage() {
  const { data: performance } = useQuery({
    queryKey: ["ai-performance"],
    queryFn: api.aiPerformance,
  });
  const { data: account } = useQuery({ queryKey: ["ai-account"], queryFn: api.aiAccount });
  const { data: history } = useQuery({ queryKey: ["ai-history"], queryFn: api.aiHistory });
  const { data: orders } = useQuery({ queryKey: ["ai-orders"], queryFn: api.aiOrders });

  const pnlPositive = (performance?.pnl_jpy ?? 0) >= 0;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-xl font-semibold">AI自動売買シミュレーション</h1>
        <p className="mt-1 text-sm text-neutral-500">
          このアプリの予想エンジンが、実際の株価だけを使って自動で売買したら資金がどう推移するかを検証します。
          元手は5万円(仮想)。実際のお金は動きません。
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card>
          <p className="text-xs text-neutral-500">元手</p>
          <p className="mt-1 text-lg font-bold">
            {performance ? formatJpy(performance.starting_cash_jpy) : "-"}
          </p>
        </Card>
        <Card>
          <p className="text-xs text-neutral-500">現在の評価額</p>
          <p className="mt-1 text-lg font-bold">
            {performance ? formatJpy(performance.total_value_jpy) : "-"}
          </p>
        </Card>
        <Card>
          <p className="text-xs text-neutral-500">損益</p>
          <p className={clsx("mt-1 text-lg font-bold", pnlPositive ? "text-up" : "text-down")}>
            {performance ? `${pnlPositive ? "+" : ""}${formatJpy(performance.pnl_jpy)}` : "-"}
          </p>
        </Card>
        <Card>
          <p className="text-xs text-neutral-500">損益率</p>
          <p className={clsx("mt-1 text-lg font-bold", pnlPositive ? "text-up" : "text-down")}>
            {performance ? `${pnlPositive ? "+" : ""}${performance.pnl_pct.toFixed(2)}%` : "-"}
          </p>
        </Card>
      </div>

      <Card>
        <h2 className="mb-2 text-sm font-medium text-neutral-500">資金推移</h2>
        {history && history.length > 1 ? (
          <EquityChart points={history} startingCash={performance?.starting_cash_jpy ?? 50000} />
        ) : (
          <p className="text-sm text-neutral-500">
            まだ推移データが十分にありません(東証の取引時間中、10分おきに記録されます)。
          </p>
        )}
      </Card>

      <Card>
        <h2 className="mb-3 text-sm font-medium text-neutral-500">保有中の銘柄</h2>
        {account && account.positions.length > 0 ? (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-neutral-500">
                <th className="pb-2 font-normal">銘柄</th>
                <th className="pb-2 text-right font-normal">数量</th>
                <th className="pb-2 text-right font-normal">取得単価</th>
                <th className="pb-2 text-right font-normal">現在値</th>
                <th className="pb-2 text-right font-normal">評価損益</th>
              </tr>
            </thead>
            <tbody>
              {account.positions.map((p) => (
                <tr key={p.code} className="border-t border-neutral-100 dark:border-neutral-800">
                  <td className="py-2">
                    {p.name} <span className="text-neutral-400">{p.code}</span>
                  </td>
                  <td className="py-2 text-right">{p.quantity}</td>
                  <td className="py-2 text-right">{p.avg_price.toLocaleString()}</td>
                  <td className="py-2 text-right">{p.current_price.toLocaleString()}</td>
                  <td
                    className={clsx(
                      "py-2 text-right",
                      p.unrealized_pnl_jpy >= 0 ? "text-up" : "text-down"
                    )}
                  >
                    {p.unrealized_pnl_jpy >= 0 ? "+" : ""}
                    {formatJpy(p.unrealized_pnl_jpy)} ({p.unrealized_pnl_pct >= 0 ? "+" : ""}
                    {p.unrealized_pnl_pct.toFixed(1)}%)
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-sm text-neutral-500">現在保有中の銘柄はありません</p>
        )}
      </Card>

      <Card>
        <h2 className="mb-3 text-sm font-medium text-neutral-500">AIの売買履歴</h2>
        <ul className="flex flex-col divide-y divide-neutral-100 dark:divide-neutral-800">
          {orders?.map((order) => (
            <li key={order.id} className="py-3 text-sm">
              <div className="flex items-center justify-between">
                <span>
                  <span className={order.side === "buy" ? "text-up" : "text-down"}>
                    {order.side === "buy" ? "買い" : "売り"}
                  </span>{" "}
                  {order.name} ({order.code}) × {order.quantity}
                </span>
                <span className="text-neutral-500">
                  @{order.fill_price.toLocaleString()} ・ {format(new Date(order.filled_at), "MM/dd HH:mm")}
                </span>
              </div>
              {order.reason && <p className="mt-1 text-xs text-neutral-500">{order.reason}</p>}
            </li>
          ))}
          {orders?.length === 0 && (
            <p className="py-4 text-sm text-neutral-500">
              まだAIによる売買はありません。東証の取引時間中に予想の確信度が高い銘柄が出ると自動で発注します。
            </p>
          )}
        </ul>
      </Card>
    </div>
  );
}
