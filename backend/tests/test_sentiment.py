from app.services import sentiment


def test_positive_text_scores_positive():
    score = sentiment.score_text("好業績で株価が急騰、上方修正を発表")
    assert score > 0
    assert sentiment.label_for_score(score) == "positive"


def test_negative_text_scores_negative():
    score = sentiment.score_text("業績悪化で株価が急落、下方修正を発表")
    assert score < 0
    assert sentiment.label_for_score(score) == "negative"


def test_neutral_text_scores_zero():
    score = sentiment.score_text("本日の東京市場の取引が終了しました")
    assert score == 0.0
    assert sentiment.label_for_score(score) == "neutral"


def test_empty_text():
    assert sentiment.score_text("") == 0.0
