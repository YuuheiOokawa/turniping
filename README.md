# turniping

日本株(個別銘柄 + 日経平均 / TOPIX連動ETF)の値動きを、実際の株価データとニュースから予想し、
市場が開いているときにリアルタイムで答え合わせしながら学ぶためのアプリ。

- **モック/合成データは使わない**。株価は Yahoo Finance の公開chart APIから、ニュースはNHK/Google NewsのRSSから実際に取得する。
- 予想はルールベース(移動平均・RSI・MACD・ボリンジャーバンド)+ニュースの簡易センチメント分析の組み合わせ。
- 予想の的中率を記録し、答え合わせを繰り返しながら「どんな時に当たりやすいか」を学べるようにしている。
- 実際のお金は動かさないペーパートレード機能で売買を練習できる。

## 構成

- `backend/`: FastAPI + SQLAlchemy(async) + PostgreSQL + APScheduler worker + Redis(価格のWS配信)
- `frontend/`: Next.js (App Router) + React Query + lightweight-charts

同一マシン内の `FXTradingLab/`(FX版)と同じ構成パターンを踏襲している。

## ローカル起動(Windows, Docker不使用)

前提: PostgreSQL 17がローカルで動いていること、`tools/redis/`にポータブルRedisがあること、Python 3.14(`py -3.14`)とNode 20が使えること。

### 初回セットアップ

```powershell
# 1. DB作成 (初回のみ)
psql -U postgres -c "CREATE ROLE turniping WITH LOGIN PASSWORD 'turniping';"
psql -U postgres -c "CREATE DATABASE turniping OWNER turniping;"
psql -U postgres -c "CREATE DATABASE turniping_test OWNER turniping;"

# 2. バックエンド
cd backend
py -3.14 -m venv .venv
.\.venv\Scripts\pip install -r requirements-dev.txt
copy .env.example .env
.\.venv\Scripts\python -m alembic upgrade head

# 3. フロントエンド
cd ..\frontend
copy .env.local.example .env.local
npm install
```

### 起動

```powershell
.\start-local.ps1
```

Redis・API(:8001)・worker・Next.js(:3002)の4ウィンドウが立ち上がる。
`APP_ENV=development`ではフロントのログインゲートとバックエンドの認証は無効化される。

- フロントエンド: http://localhost:3002
- API docs: http://localhost:8001/docs

### テスト

```powershell
# backend
cd backend
.\.venv\Scripts\python -m pytest

# frontend
cd frontend
npm run typecheck
npm run build
npx vitest run
```

## 銘柄の追加

デフォルトのウォッチリストは`backend/app/instruments_catalog.py`で管理しており、現在79銘柄
(日経平均・TOPIX連動ETFに加え、自動車・電機精密・半導体/電子部品・通信/IT・銀行・証券金融・商社・小売・医薬品・鉄鋼素材・化学・機械重工業・不動産・運輸・食品/生活必需品・エネルギー・エンタメなど主要セクターを分散してカバー、全銘柄Yahoo Financeでの取得確認済み)。
一部銘柄だけで始めたい場合は`.env`の`DEFAULT_WATCHLIST`で上書きできる。
ダッシュボード画面から証券コード(例: `9432.T`)を入力すればさらに追加でき、Yahoo Financeから銘柄名を自動取得する。

## 情報収集(常時)

- 株価: 東証の立会時間(前場9:00-11:30, 後場12:30-15:00 JST、土日祝休場)中は30秒間隔でポーリング。
- ニュース: 5分間隔で、ウォッチリスト銘柄ごとのニュースに加え、国内景気(NHK経済)・世界経済(NHK国際)・米国株式市場・FRBの金融政策・為替・原油価格・中国経済など、値動きに影響しうる世界の情報を市場が閉まっている時間帯も含めて常時収集する。
- 予想: 10分間隔でテクニカル指標+直近24時間のニュースセンチメントから再計算。

## 注意

- 価格ポーリングのみ東証の立会時間限定。ニュース収集と予想計算は24時間動く(workerプロセスを起動している間)。
- ニュースのセンチメント判定はキーワード辞書によるシンプルな方式であり、投資判断の根拠として十分な精度は保証しない。
- ここでの「予想」は学習・検証目的であり、実際の投資助言ではない。
