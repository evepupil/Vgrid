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
  drawdown_curve: { ts: string; drawdown: string }[] // FR-7.3 逐点回撤（<=0）
  buy_hold_curve: { ts: string; equity: string }[] // FR-7.3 买入持有对照
  fills: Fill[]
  n_bars: number
  end_ladder: LadderView | null // FR-7.4 期末阶梯快照
  overfit_note: string // FR-7.5 样本内最优提示
}

export interface BacktestBody {
  start: string
  end: string
  frame?: string
  config: StrategyConfig
  symbol?: string
}

export async function runBacktest(body: BacktestBody): Promise<BacktestResult> {
  return post<BacktestResult>('/api/backtest', body)
}

// 参数扫描（FR-8）
export type ScanMetric = 'sharpe' | 'total_return' | 'annualized_return' | 'calmar'

export interface ScanBody {
  start: string
  end: string
  frame?: string
  fixed: Record<string, unknown> // 固定字段（含 symbol）
  vary: Record<string, unknown[]> // 扫描字段 → 候选值
  metric?: ScanMetric
  top?: number
}

export interface ScanRow {
  params: Record<string, string | number> // 该组扫描字段的取值
  metrics: {
    sharpe: string
    total_return: string
    annualized_return: string
    max_drawdown: string
    win_rate: string
    final_equity: string
    n_buys: number
    n_sells: number
  }
}

export interface ScanResult {
  metric: string
  total: number // 扫了多少组
  shown: number // 回了前几组
  vary_keys: string[]
  rows: ScanRow[]
  overfit_note: string
}

export async function runScan(body: ScanBody): Promise<ScanResult> {
  return post<ScanResult>('/api/scan', body)
}

// 网格阶梯（FR-4）
export type LadderKind = 'sell' | 'buy' | 'capped' | 'idle'

export interface LadderRung {
  price: string
  depth: number // 0=基准窗口，>0=向下放大区
  kind: LadderKind
  held_shares: number // kind==sell 时>0
}

export interface LadderView {
  rungs: LadderRung[] // 低→高
  current_price: string
  cap_price: string | null // 资金上限触及价，无则 null
  window_lower: string
  window_upper: string
  step: string
  grid_count: number
  spacing_mode: string
}

/** 按 config 在某价位预览一条阶梯（缺省价用窗口中点）。 */
export async function previewLadder(
  config: StrategyConfig,
  price: string | null = null,
): Promise<LadderView> {
  return post<LadderView>('/api/ladder/preview', { config, price })
}

// 实时报价（FR-11.1 / 11.4）
export interface Quote {
  symbol: string
  name: string | null
  price: string
  prev_close: string | null // 昨收
  change: string | null // 涨跌额
  change_pct: string | null // 涨跌幅（%）
}

export interface QuotesResponse {
  quotes: Quote[]
  error: string | null // 行情源失败时非空，前端降级为占位
}

/** 批量取多标的实时报价（现价 + 昨收 + 涨跌）。 */
export async function getQuotes(symbols: string[]): Promise<QuotesResponse> {
  if (symbols.length === 0) return { quotes: [], error: null }
  return get<QuotesResponse>(`/api/quotes?symbols=${encodeURIComponent(symbols.join(','))}`)
}

// portfolio
export interface PortfolioSummary {
  n_instances: number
  n_running: number
  total_equity: string
  total_realized_pnl: string
  total_unrealized_pnl: string // 浮动合计（跨标的净敞口）
  total_committed: string // 占用合计
  total_cap: string // 总额度合计
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
  unrealized_pnl: string // 浮动
  committed: string // 占用
  capital_cap: string // 资金上限
  position_shares: number
  sharpe: string
  max_drawdown: string
  total_fee: string
  open_lots: number
  n_fills: number
  equity_spark: string[] // 迷你净值（降采样 ~24 点）
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

// 关注列表增强（FR-10.2~10.4）：实时行情 + 振幅 + 网格适配评分 + 近 N 日走势
export interface EnrichedWatch {
  symbol: string
  name: string | null
  added_at: string
  price: string | null
  change_pct: string | null // 涨跌%
  amplitude_pct: string | null // 平均日振幅%
  fitness_score: number | null // 网格适配评分 0–100
  trendiness: string | null // 效率比 [0,1]，越大越单边
  crossings: number | null // 收盘穿越均线次数
  trend: string[] // 近 N 日收盘（sparkline），空则不画
  error: string | null // 该行历史行情失败时非空
}

export async function listWatchlistEnriched(): Promise<EnrichedWatch[]> {
  return get<EnrichedWatch[]>('/api/watchlist/enriched')
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

// ETF 信息
export interface EtfInfo {
  symbol: string
  name: string
}

export async function getEtfInfo(symbol: string): Promise<EtfInfo> {
  return get<EtfInfo>(`/api/etf/${encodeURIComponent(symbol)}/info`)
}

// 单实例看盘
export interface StateConfig {
  symbol: string
  lower_price: string
  upper_price: string
  grid_count: number
  spacing_mode: string
  base_build_mode: string
  capital_cap: string
  per_grid_amount: string
}

export interface StateSnapshot {
  last_price: string | null
  last_ts: string | null
  open_lots: number
  committed: string
  realized_pnl: string // 已实现（累计套利）
  unrealized_pnl: string // 浮动（持仓 mark-to-market）—— 与已实现分开
  position_shares: number
  position_value: string
  avg_cost: string
  total_fee: string
  cash_flow: string
  n_fills: number
}

export interface StateView {
  symbol: string
  config: StateConfig
  snapshot: StateSnapshot
  metrics: {
    total_return: string
    max_drawdown: string
    sharpe: string
    buy_hold_return: string
  }
  fills: Fill[]
  equity_curve: EquityPoint[]
  drawdown_curve: { ts: string; drawdown: string }[] // 逐点回撤比例（<=0）
  buy_hold_curve: { ts: string; equity: string }[] // 买入持有逐点权益
  fill_marks: {
    index: number
    side: 'buy' | 'sell'
    price: string
    shares: number
    realized_pnl?: string
  }[]
  n_ticks: number
  ladder: LadderView | null
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
