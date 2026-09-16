"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";

const SIGNAL_LABELS: Record<string, string> = {
  sma_cross: "移動平均クロス",
  rsi: "RSI",
  macd: "MACD",
  bollinger: "ボリンジャーバンド",
  sentiment: "ニュースセンチメント",
  market_regime: "相場全体(日経平均)との整合性",
};

export default function AccuracyPage() {
  const { data: overall } = useQuery({ queryKey: ["accuracy-overall"], queryFn: api.accuracyOverall });
  const { data: instruments } = useQuery({ queryKey: ["instruments"], queryFn: api.instruments });
  const { data: weights } = useQuery({ queryKey: ["strategy-weights"], queryFn: api.strategyWeights });

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">予想の的中率</h1>
      <p className="text-sm text-neutral-500">
        予想が的中したかどうかは、予想時刻から一定時間(既定60分)経過後の実際の値動きと照合して記録しています。
        この数字を見ながら「どんな時に予想が当たりやすいか」を学んでいきましょう。
      </p>

      <Card>
        <h2 className="mb-2 text-sm font-medium text-neutral-500">全体</h2>
        {overall ? (
          <div className="flex items-baseline gap-4">
            <span className="text-3xl font-bold">
              {overall.accuracy_pct !== null ? `${overall.accuracy_pct.toFixed(1)}%` : "-"}
            </span>
            <span className="text-sm text-neutral-500">
              {overall.correct} / {overall.total_evaluated} 件的中
            </span>
          </div>
        ) : (
          <p className="text-sm text-neutral-500">読み込み中...</p>
        )}
      </Card>

      <Card>
        <h2 className="mb-1 text-sm font-medium text-neutral-500">学習状況(自己学習)</h2>
        <p className="mb-3 text-xs text-neutral-500">
          答え合わせの実績をもとに、各シグナルが単独でどれだけ方向を当てられていたかを定期的に振り返り、
          的中率が高いシグナルほど重み(発言力)を強め、外れが多いシグナルほど弱めています(1.0が既定値)。
          十分な件数(20件)が溜まるまではまだ調整されません。
        </p>
        {weights && weights.length > 0 ? (
          <ul className="flex flex-col divide-y divide-neutral-100 dark:divide-neutral-800">
            {weights.map((w) => (
              <li key={w.signal_name} className="flex items-center justify-between py-2 text-sm">
                <span>{SIGNAL_LABELS[w.signal_name] ?? w.signal_name}</span>
                <span className="text-neutral-500">
                  重み {w.weight.toFixed(2)} ・ 的中率 {w.accuracy_pct?.toFixed(1)}% ({w.sample_size}件)
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-neutral-500">
            まだ学習に十分な答え合わせ件数が溜まっていません(シグナルごとに20件以上必要)。データが蓄積され次第、自動で調整が始まります。
          </p>
        )}
      </Card>

      <Card>
        <h2 className="mb-3 text-sm font-medium text-neutral-500">銘柄別</h2>
        <ul className="flex flex-col divide-y divide-neutral-100 dark:divide-neutral-800">
          {instruments?.map((instrument) => (
            <InstrumentAccuracyRow key={instrument.code} code={instrument.code} name={instrument.name} />
          ))}
        </ul>
      </Card>
    </div>
  );
}

function InstrumentAccuracyRow({ code, name }: { code: string; name: string }) {
  const { data } = useQuery({
    queryKey: ["accuracy", code],
    queryFn: () => api.accuracyForInstrument(code),
  });

  return (
    <li className="flex items-center justify-between py-2 text-sm">
      <span>
        {name} <span className="text-neutral-400">{code}</span>
      </span>
      <span>
        {data && data.total_evaluated > 0
          ? `${data.accuracy_pct?.toFixed(1)}% (${data.correct}/${data.total_evaluated})`
          : "評価中"}
      </span>
    </li>
  );
}
