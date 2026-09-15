"""日本語キーワード辞書ベースの簡易センチメント判定。ML/外部APIは使わずルールベースで完結させる。"""

POSITIVE_WORDS = [
    "上昇", "急騰", "最高益", "増益", "好調", "黒字", "上方修正", "買い", "利上げ期待",
    "円安", "業績拡大", "強気", "回復", "反発", "高値更新", "好材料", "堅調", "拡大",
    "成長", "record high", "surge", "rally",
]

NEGATIVE_WORDS = [
    "下落", "急落", "赤字", "減益", "業績悪化", "下方修正", "売り", "利下げ",
    "円高", "弱気", "後退", "反落", "安値更新", "悪材料", "低迷", "縮小", "懸念",
    "リスク", "暴落", "warning", "slump", "recession",
]


def score_text(text: str) -> float:
    """-1.0(強いネガティブ)〜+1.0(強いポジティブ)のスコアを返す。"""
    if not text:
        return 0.0
    pos_hits = sum(text.count(w) for w in POSITIVE_WORDS)
    neg_hits = sum(text.count(w) for w in NEGATIVE_WORDS)
    total = pos_hits + neg_hits
    if total == 0:
        return 0.0
    return (pos_hits - neg_hits) / total


def label_for_score(score: float) -> str:
    if score > 0.15:
        return "positive"
    if score < -0.15:
        return "negative"
    return "neutral"
