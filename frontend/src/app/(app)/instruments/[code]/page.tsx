"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { DirectionBadge } from "@/components/prediction/DirectionBadge";
import { CandleChart } from "@/components/chart/CandleChart";
import { format } from "date-fns";

export default function InstrumentDetailPage() {
  const params = useParams<{ code: string }>();
  const code = decodeURIComponent(params.code);

  const { data: candles } = useQuery({
    queryKey: ["candles", code],
    queryFn: () => api.candles(code, "1d", 90),
  });
  const { data: prediction } = useQuery({
    queryKey: ["prediction", code],
    queryFn: () => api.latestPrediction(code),
  });
  const { data: news } = useQuery({
    queryKey: ["news", code],
    queryFn: () => api.news(code),
  });
  const { data: accuracy } = useQuery({
    queryKey: ["accuracy", code],
    queryFn: () => api.accuracyForInstrument(code),
  });

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">{code}</h1>

      <Card>
        <h2 className="mb-2 text-sm font-medium text-neutral-500">日足チャート</h2>
        {candles && candles.length > 0 ? (
          <CandleChart candles={candles} />
        ) : (
          <p className="text-sm text-neutral-500">データがありません</p>
        )}
      </Card>

      <Card>
        <h2 className="mb-2 text-sm font-medium text-neutral-500">予想</h2>
        {prediction ? (
          <div className="flex flex-col gap-2">
            <DirectionBadge direction={prediction.direction} confidence={prediction.confidence} />
            <p className="text-xs text-neutral-500">
              {format(new Date(prediction.created_at), "MM/dd HH:mm")} 時点 / 基準値{" "}
              {prediction.reference_price.toLocaleString()}
            </p>
            <ul className="list-inside list-disc text-sm">
              {prediction.reasons.map((reason, i) => (
                <li key={i}>{reason}</li>
              ))}
            </ul>
            {accuracy && accuracy.total_evaluated > 0 && (
              <p className="text-xs text-neutral-500">
                この銘柄の的中率: {accuracy.accuracy_pct?.toFixed(1)}% ({accuracy.correct}/{accuracy.total_evaluated})
              </p>
            )}
          </div>
        ) : (
          <p className="text-sm text-neutral-500">まだ予想がありません</p>
        )}
      </Card>

      <Card>
        <h2 className="mb-2 text-sm font-medium text-neutral-500">関連ニュース</h2>
        <ul className="flex flex-col gap-3">
          {news?.map((article) => (
            <li key={article.id} className="text-sm">
              <a href={article.url} target="_blank" rel="noreferrer" className="hover:underline">
                {article.title}
              </a>
              <div className="text-xs text-neutral-500">
                {article.source} ・ {format(new Date(article.published_at), "MM/dd HH:mm")} ・{" "}
                <span
                  className={
                    article.sentiment_label === "positive"
                      ? "text-up"
                      : article.sentiment_label === "negative"
                        ? "text-down"
                        : ""
                  }
                >
                  {article.sentiment_label}
                </span>
              </div>
            </li>
          ))}
          {news?.length === 0 && <p className="text-sm text-neutral-500">関連ニュースがありません</p>}
        </ul>
      </Card>
    </div>
  );
}
