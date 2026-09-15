import { Card } from "@/components/ui/card";

const TERMS = [
  {
    term: "移動平均線(SMA/EMA)",
    body: "一定期間の株価の平均値を結んだ線。短期線が中期線を上回ると上昇トレンド入りのサイン(ゴールデンクロス)、下回ると下降トレンド入りのサイン(デッドクロス)とされます。",
  },
  {
    term: "RSI(相対力指数)",
    body: "0〜100で表され、70を超えると「買われすぎ」、30を下回ると「売られすぎ」とされる指標。行き過ぎた水準からの反動を狙う際の目安になります。",
  },
  {
    term: "MACD",
    body: "短期と中期の移動平均線の差(MACDライン)と、その平滑化線(シグナルライン)を比較してトレンドの勢いを見る指標。MACDラインがシグナルラインを上回るほど上昇の勢いが強いとされます。",
  },
  {
    term: "ボリンジャーバンド",
    body: "移動平均線の上下に標準偏差の帯を描いたもの。株価が上限に近づくと反落、下限に近づくと反発が意識されやすいとされます。",
  },
  {
    term: "東証の立会時間",
    body: "前場9:00〜11:30、後場12:30〜15:00(土日・祝日は休場)。このアプリはこの時間帯のみリアルタイムに近い値動きを取得します。",
  },
  {
    term: "センチメント分析",
    body: "ニュースの見出しや本文にポジティブ/ネガティブな単語がどれだけ含まれるかを数えて景気や株価への影響を推測する手法。このアプリではキーワード辞書によるシンプルな方式を採用しています。",
  },
  {
    term: "ペーパートレード",
    body: "実際のお金を使わず、実際の株価だけを使って売買を練習すること。損益の感覚をつかみながらリスクなく学べます。",
  },
];

export default function GuidePage() {
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">用語ガイド</h1>
      <p className="text-sm text-neutral-500">
        このアプリの予想根拠に出てくる用語を解説します。まずは実際の予想画面の根拠と見比べながら読んでみてください。
      </p>
      <div className="grid gap-4 sm:grid-cols-2">
        {TERMS.map((t) => (
          <Card key={t.term}>
            <h2 className="mb-1 font-medium">{t.term}</h2>
            <p className="text-sm text-neutral-600 dark:text-neutral-300">{t.body}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}
