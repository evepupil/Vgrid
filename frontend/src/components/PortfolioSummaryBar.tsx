import type { PortfolioSummary } from '../api/client'
import { fmt, upDown } from '../utils/format'

interface Props {
  summary: PortfolioSummary | undefined
  simMode: boolean
}

/** 千元档：把「¥ 12345」显示成「12k」，占用/额度用。 */
function k(v: number): string {
  return `${(v / 1000).toFixed(0)}k`
}

/** 组合汇总条（FR-2.1）：总资产 · 已实现合计 · 浮动合计 · 占用/总额度。 */
export function PortfolioSummaryBar({ summary, simMode }: Props) {
  const equity = Number(summary?.total_equity ?? 0)
  const realized = Number(summary?.total_realized_pnl ?? 0)
  const floating = Number(summary?.total_unrealized_pnl ?? 0)
  const used = Number(summary?.total_committed ?? 0)
  const cap = Number(summary?.total_cap ?? 0)
  const n = summary?.n_instances ?? 0
  const pct = cap > 0 ? Math.round((used / cap) * 100) : 0

  return (
    <div className="pf-sum rise d1">
      <div className="c">
        <span className="k">{simMode ? '模拟总资产' : '总资产'}</span>
        <span className="v">¥ {fmt(equity, 0)}</span>
        <span className="s">{n} 个实例聚合</span>
      </div>
      <div className="c">
        <span className="k">已实现盈亏合计</span>
        <span className={`v ${upDown(realized)}`}>
          {realized >= 0 ? '+' : '−'}¥ {fmt(Math.abs(realized), 0)}
        </span>
        <span className="s">累计套利落袋</span>
      </div>
      <div className="c">
        <span className="k">持仓浮动合计</span>
        <span className={`v ${upDown(floating)}`}>
          {floating >= 0 ? '+' : '−'}¥ {fmt(Math.abs(floating), 0)}
        </span>
        <span className="s">跨标的净敞口</span>
      </div>
      <div className="c">
        <span className="k">占用 / 总额度</span>
        <span className="v">¥ {k(used)}</span>
        <span className="s">
          / {k(cap)} · {pct}%
        </span>
      </div>
    </div>
  )
}
