import type { BacktestBody, StrategyConfig } from '../api/client'

/** 回测表单状态：全部存字符串（受控输入友好），提交时按需转数字。 */
export interface BtForm {
  symbol: string
  start: string
  end: string
  frame: string
  lower_price: string
  upper_price: string
  grid_count: string
  per_grid_amount: string
  capital_cap: string
  spacing_mode: string // arithmetic | geometric
  base_build_mode: string // center | zero
}

export function defaultForm(symbol: string): BtForm {
  return {
    symbol,
    start: '2024-01-01',
    end: '2025-07-01',
    frame: '1d',
    lower_price: '1.000',
    upper_price: '1.350',
    grid_count: '20',
    per_grid_amount: '2000',
    capital_cap: '50000',
    spacing_mode: 'arithmetic',
    base_build_mode: 'center',
  }
}

/** 表单 → GridConfig dict（grid_count 转数字，其余 Decimal 字段留字符串保精度）。 */
export function toConfig(f: BtForm): StrategyConfig {
  return {
    symbol: f.symbol,
    lower_price: f.lower_price,
    upper_price: f.upper_price,
    grid_count: Number(f.grid_count),
    per_grid_amount: f.per_grid_amount,
    capital_cap: f.capital_cap,
    spacing_mode: f.spacing_mode,
    base_build_mode: f.base_build_mode,
  }
}

export function toBacktestBody(f: BtForm): BacktestBody {
  return { start: f.start, end: f.end, frame: f.frame, config: toConfig(f), symbol: f.symbol }
}
