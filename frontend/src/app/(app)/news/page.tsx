"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { format } from "date-fns";

export default function NewsPage() {
  const { data: news, isLoading } = useQuery({ queryKey: ["news-all"], queryFn: () => api.news() });

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">ニュースフィード</h1>
      {isLoading && <p className="text-sm text-neutral-500">読み込み中...</p>}
      <Card>
        <ul className="flex flex-col divide-y divide-neutral-100 dark:divide-neutral-800">
          {news?.map((article) => (
            <li key={article.id} className="py-3 text-sm">
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
        </ul>
        {news?.length === 0 && <p className="py-4 text-sm text-neutral-500">まだニュースがありません</p>}
      </Card>
    </div>
  );
}
