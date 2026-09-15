"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { format } from "date-fns";

export default function PaperTradingPage() {
  const queryClient = useQueryClient();
  const [code, setCode] = useState("");
  const [quantity, setQuantity] = useState(100);

  const { data: account } = useQuery({ queryKey: ["paper-account"], queryFn: api.paperAccount });
  const { data: orders } = useQuery({ queryKey: ["paper-orders"], queryFn: api.paperOrders });

  const orderMutation = useMutation({
    mutationFn: ({ side }: { side: "buy" | "sell" }) => api.placeOrder(code, side, quantity),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["paper-account"] });
      queryClient.invalidateQueries({ queryKey: ["paper-orders"] });
    },
  });

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">ペーパートレード</h1>
      <p className="text-sm text-neutral-500">
        実際の現在値を使い、仮想の現金で売買を練習できます(実際のお金は動きません)。
      </p>

      <Card>
        <h2 className="mb-2 text-sm font-medium text-neutral-500">口座</h2>
        {account && (
          <div className="flex flex-col gap-2">
            <p className="text-2xl font-bold">¥{account.cash_jpy.toLocaleString()}</p>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-neutral-500">
                  <th className="pb-1 font-normal">銘柄</th>
                  <th className="pb-1 text-right font-normal">保有数</th>
                  <th className="pb-1 text-right font-normal">平均取得単価</th>
                </tr>
              </thead>
              <tbody>
                {account.positions.map((p) => (
                  <tr key={p.code}>
                    <td>{p.name} ({p.code})</td>
                    <td className="text-right">{p.quantity}</td>
                    <td className="text-right">{p.avg_price.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {account.positions.length === 0 && (
              <p className="text-sm text-neutral-500">保有中の銘柄はありません</p>
            )}
          </div>
        )}
      </Card>

      <Card>
        <h2 className="mb-2 text-sm font-medium text-neutral-500">発注</h2>
        <div className="flex flex-wrap items-center gap-2">
          <input
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="銘柄コード 例: 7203.T"
            className="rounded border border-neutral-300 px-2 py-1 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          />
          <input
            type="number"
            value={quantity}
            onChange={(e) => setQuantity(Number(e.target.value))}
            min={1}
            className="w-24 rounded border border-neutral-300 px-2 py-1 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          />
          <button
            onClick={() => orderMutation.mutate({ side: "buy" })}
            className="rounded bg-up px-3 py-1 text-sm text-white"
          >
            買い
          </button>
          <button
            onClick={() => orderMutation.mutate({ side: "sell" })}
            className="rounded bg-down px-3 py-1 text-sm text-white"
          >
            売り
          </button>
        </div>
        {orderMutation.isError && (
          <p className="mt-2 text-sm text-up">{(orderMutation.error as Error).message}</p>
        )}
      </Card>

      <Card>
        <h2 className="mb-2 text-sm font-medium text-neutral-500">注文履歴</h2>
        <ul className="flex flex-col divide-y divide-neutral-100 text-sm dark:divide-neutral-800">
          {orders?.map((order) => (
            <li key={order.id} className="flex justify-between py-2">
              <span>
                {order.side === "buy" ? "買い" : "売り"} {order.code} × {order.quantity}
              </span>
              <span className="text-neutral-500">
                @{order.fill_price.toLocaleString()} ・ {format(new Date(order.filled_at), "MM/dd HH:mm")}
              </span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
