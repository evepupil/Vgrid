import type { DcaBacktestBody, StrategyConfig } from '../api/client'

/** 跌幅加码的一档（回撤阈值 + 金额倍数），都存字符串保精度。 */
export interface DcaTierForm {
  drawdown: string
  multiplier: string
}

/** 定投表单状态：全部存字符串（受控输入友好），提交时按需转数字。 */
export interface DcaForm {
  symbol: string
  start: string
  end: string
  frame: string
  frequency: string // daily | weekly | monthly
  weekday: string // 1..7（weekly 用）
  day_of_month: string // 1..31（monthly 用）
  base_amount: string
  cash_cap: string
  mode: string // fixed | drawdown | ma_deviation
  // drawdown
  lookback_days: string
  tiers: DcaTierForm[]
  // ma_deviation
  ma_window: string
  below_multiplier: string
  normal_multiplier: string
  above_multiplier: string
}

export function defaultDcaForm(symbol: string): DcaForm {
  return {
    symbol,
    start: '2024-01-01',
    end: '2025-07-01',
    frame: '1d',
    frequency: 'weekly',
    weekday: '1',
    day_of_month: '1',
    base_amount: '2000',
    cash_cap: '50000',
    mode: 'fixed',
    lookback_days: '120',
    tiers: [
      { drawdown: '0.05', multiplier: '1.5' },
      { drawdown: '0.10', multiplier: '2' },
    ],
    ma_window: '60',
    below_multiplier: '1.5',
    normal_multiplier: '1',
    above_multiplier: '0.5',
  }
}

/** 表单 → 金额规则 dict（按 mode 只带相关字段）。 */
function toPolicy(f: DcaForm): Record<string, unknown> {
  if (f.mode === 'drawdown') {
    return {
      mode: 'drawdown',
      lookback_days: Number(f.lookback_days),
      tiers: f.tiers.map((t) => ({ drawdown: t.drawdown, multiplier: t.multiplier })),
    }
  }
  if (f.mode === 'ma_deviation') {
    return {
      mode: 'ma_deviation',
      ma_window: Number(f.ma_window),
      below_multiplier: f.below_multiplier,
      normal_multiplier: f.normal_multiplier,
      above_multiplier: f.above_multiplier,
    }
  }
  return { mode: 'fixed' }
}

/** 表单 → DcaConfig dict（数字字段转 Number，Decimal 字段留字符串保精度）。 */
export function toDcaConfig(f: DcaForm): StrategyConfig {
  return {
    type: 'dca',
    symbol: f.symbol,
    frequency: f.frequency,
    weekday: Number(f.weekday),
    day_of_month: Number(f.day_of_month),
    base_amount: f.base_amount,
    cash_cap: f.cash_cap,
    amount_policy: toPolicy(f),
  }
}

export function toDcaBody(f: DcaForm): DcaBacktestBody {
  return { start: f.start, end: f.end, frame: f.frame, config: toDcaConfig(f), symbol: f.symbol }
}
