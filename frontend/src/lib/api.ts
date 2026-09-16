export type Instrument = {
  code: string;
  name: string;
  kind: "individual" | "index";
  last_price: number | null;
  change_pct: number | null;
};

export type Candle = {
  ts: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type Prediction = {
  id: number;
  created_at: string;
  horizon_minutes: number;
  direction: "up" | "down";
  confidence: number;
  technical_score: number;
  sentiment_score: number;
  reference_price: number;
  reasons: string[];
};

export type NewsArticle = {
  id: number;
  source: string;
  url: string;
  title: string;
  summary: string | null;
  published_at: string;
  sentiment_score: number;
  sentiment_label: "positive" | "negative" | "neutral";
};

export type PaperPosition = {
  code: string;
  name: string;
  quantity: number;
  avg_price: number;
};

export type PaperAccount = {
  cash_jpy: number;
  positions: PaperPosition[];
};

export type PaperOrder = {
  id: number;
  code: string;
  side: "buy" | "sell";
  quantity: number;
  fill_price: number;
  filled_at: string;
};

export type SystemStatus = {
  now_jst: string;
  market_open: boolean;
  next_open_jst: string | null;
};

export type AccuracyStats = {
  total_evaluated: number;
  correct: number;
  accuracy_pct: number | null;
};

export type StrategySignalWeight = {
  signal_name: string;
  weight: number;
  accuracy_pct: number | null;
  sample_size: number;
  updated_at: string;
};

export type BacktestSummary = {
  total_samples: number;
  instrument_count: number;
  earliest_date: string | null;
  latest_date: string | null;
};

export type AiPosition = {
  code: string;
  name: string;
  quantity: number;
  avg_price: number;
  current_price: number;
  market_value: number;
  unrealized_pnl_jpy: number;
  unrealized_pnl_pct: number;
};

export type AiAccount = {
  cash_jpy: number;
  holdings_value_jpy: number;
  total_value_jpy: number;
  positions: AiPosition[];
};

export type AiPerformance = {
  starting_cash_jpy: number;
  cash_jpy: number;
  holdings_value_jpy: number;
  total_value_jpy: number;
  pnl_jpy: number;
  pnl_pct: number;
};

export type AiOrder = {
  id: number;
  code: string;
  name: string;
  side: "buy" | "sell";
  quantity: number;
  fill_price: number;
  filled_at: string;
  reason: string | null;
};

export type AiValuationPoint = {
  ts: string;
  cash_jpy: number;
  holdings_value_jpy: number;
  total_value_jpy: number;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api/backend/${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API error ${res.status}: ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  systemStatus: () => request<SystemStatus>("system/status"),
  instruments: () => request<Instrument[]>("market/instruments"),
  candles: (code: string, timeframe: "1m" | "1d" = "1d", limit = 90) =>
    request<Candle[]>(`market/instruments/${code}/candles?timeframe=${timeframe}&limit=${limit}`),
  addWatchlist: (code: string) =>
    request<{ code: string; name: string }>("market/watchlist", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),
  removeWatchlist: (code: string) =>
    request<void>(`market/watchlist/${code}`, { method: "DELETE" }),
  latestPrediction: (code: string) => request<Prediction | null>(`predictions/${code}/latest`),
  predictionHistory: (code: string) => request<Prediction[]>(`predictions/${code}/history`),
  accuracyOverall: () => request<AccuracyStats>("predictions/accuracy/overall"),
  strategyWeights: () => request<StrategySignalWeight[]>("predictions/strategy-weights"),
  backtestSummary: () => request<BacktestSummary>("predictions/backtest-summary"),
  accuracyForInstrument: (code: string) =>
    request<AccuracyStats & { code: string }>(`predictions/${code}/accuracy`),
  news: (code?: string) => request<NewsArticle[]>(`news${code ? `?code=${code}` : ""}`),
  paperAccount: () => request<PaperAccount>("paper/account"),
  paperOrders: () => request<PaperOrder[]>("paper/orders"),
  placeOrder: (code: string, side: "buy" | "sell", quantity: number) =>
    request<PaperOrder>("paper/orders", {
      method: "POST",
      body: JSON.stringify({ code, side, quantity }),
    }),
  aiAccount: () => request<AiAccount>("ai-trading/account"),
  aiPerformance: () => request<AiPerformance>("ai-trading/performance"),
  aiOrders: () => request<AiOrder[]>("ai-trading/orders"),
  aiHistory: () => request<AiValuationPoint[]>("ai-trading/history"),
};
