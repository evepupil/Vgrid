// 策略库
export interface StrategySummary {
  name: string
  symbol: string
  spacing_mode: string
  base_build_mode: string
  grid_count: number
  lower_price: string
  upper_price: string
}

export type StrategyConfig = Record<string, unknown>

export async function listStrategies(): Promise<StrategySummary[]> {
  return get<StrategySummary[]>('/api/strategies')
}

export async function getStrategy(name: string): Promise<StrategyConfig> {
  return get<StrategyConfig>(`/api/strategies/${encodeURIComponent(name)}`)
}

export async function createStrategy(
  name: string,
  config: StrategyConfig,
): Promise<StrategyConfig> {
  return post<StrategyConfig>('/api/strategies', { name, config })
}

export async function updateStrategy(
  name: string,
  config: StrategyConfig,
): Promise<StrategyConfig> {
  return put<StrategyConfig>(`/api/strategies/${encodeURIComponent(name)}`, config)
}

export async function deleteStrategy(name: string): Promise<void> {
  await del(`/api/strategies/${encodeURIComponent(name)}`)
}

// 回测
export interface BacktestMetrics {
  initial_cash: string
  final_equity: string
  total_return: string
  annualized_return: string
  max_drawdown: string
  sharpe: string
  win_rate: string
  profit_loss_ratio: string
  n_buys: number
  n_sells: number
  total_fee: string
  buy_hold_return: string
}

export interface EquityPoint {
  ts: string
  equity: string
}

export interface Fill {
  ts: string
  side: 'buy' | 'sell'
  price: string
  shares: number
  fee: string
  realized_pnl?: string
}

export interface BacktestResult {
  metrics: BacktestMetrics
  equity_curve: EquityPoint[]
  fills: Fill[]
  n_bars: number
}

export interface BacktestBody {
  start: string
  end: string
  frame?: string
  config: StrategyConfig
}

export async function runBacktest(body: BacktestBody): Promise<BacktestResult> {
  return post<BacktestResult>('/api/backtest', body)
}

// portfolio
export interface PortfolioSummary {
  n_instances: number
  n_running: number
  total_equity: string
  total_realized_pnl: string
  total_fee: string
}

export interface InstanceView {
  name: string
  db_path: string
  symbol: string
  status: string
  last_price: string | null
  last_ts: string | null
  equity: string
  realized_pnl: string
  total_fee: string
  open_lots: number
  n_fills: number
}

export async function getPortfolioSummary(): Promise<PortfolioSummary> {
  return get<PortfolioSummary>('/api/portfolio/summary')
}

export async function listRunners(): Promise<InstanceView[]> {
  return get<InstanceView[]>('/api/portfolio/runners')
}

// 关注列表
export interface WatchItem {
  symbol: string
  name: string | null
  added_at: string
}

export async function listWatchlist(): Promise<WatchItem[]> {
  return get<WatchItem[]>('/api/watchlist')
}

export async function addWatch(
  symbol: string,
  name: string | null = null,
): Promise<unknown> {
  return post<unknown>('/api/watchlist', { symbol, name })
}

export async function removeWatch(symbol: string): Promise<void> {
  await del(`/api/watchlist/${encodeURIComponent(symbol)}`)
}

// 单实例看盘
export interface StateView {
  symbol: string
  config: Record<string, unknown>
  snapshot: Record<string, unknown>
  metrics: {
    total_return: string
    max_drawdown: string
    sharpe: string
    buy_hold_return: string
  }
  fills: Fill[]
  equity_curve: EquityPoint[]
  fill_marks: {
    index: number
    side: 'buy' | 'sell'
    price: string
    shares: number
    realized_pnl?: string
  }[]
  n_ticks: number
}

export async function getState(db: string): Promise<StateView> {
  return get<StateView>(`/api/state?db=${encodeURIComponent(db)}`)
}

// helpers
async function get<T>(url: string): Promise<T> {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`)
  return (await r.json()) as T
}

async function post<T>(url: string, body: unknown): Promise<T> {
  return send<T>(url, 'POST', body)
}

async function put<T>(url: string, body: unknown): Promise<T> {
  return send<T>(url, 'PUT', body)
}

async function del(url: string): Promise<void> {
  const r = await fetch(url, { method: 'DELETE' })
  if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`)
}

async function send<T>(url: string, method: string, body: unknown): Promise<T> {
  const r = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!r.ok) throw new Error(`${r.status}: ${await r.text()}`)
  return (await r.json()) as T
}
