import type { IncomeCompareBody } from '../api/client'

/** 红利对比表单状态：keywords 逗号分隔（空→默认红利池）/ 或 symbols 直给（给了跳过关键词）。 */
export interface IncomeForm {
  keywords: string // 逗号分隔
  symbols: string // 逗号分隔，给了就跳过关键词筛
  start: string
  end: string
  initial_cash: string
}

export function defaultIncomeForm(): IncomeForm {
  return {
    keywords: '红利,红利低波,央企红利,国企红利,高股息',
    symbols: '',
    start: '2021-01-01',
    end: '2025-07-01',
    initial_cash: '100000',
  }
}

function splitCsv(s: string): string[] | null {
  const v = s
    .split(',')
    .map((x) => x.trim())
    .filter(Boolean)
  return v.length ? v : null
}

/** 表单 → 请求体：symbols 给了跳过关键词；都没给传 null（后端用默认红利池）。 */
export function toIncomeBody(f: IncomeForm): IncomeCompareBody {
  const symbols = splitCsv(f.symbols)
  const keywords = splitCsv(f.keywords)
  return {
    start: f.start,
    end: f.end,
    initial_cash: f.initial_cash,
    symbols: symbols ?? undefined,
    keywords: symbols ? undefined : keywords ?? null,
  }
}
