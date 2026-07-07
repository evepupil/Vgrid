import type { ReactNode } from 'react'
import type { StateView } from '../api/client'
import { fmt, priceDecimals, upDown } from '../utils/format'

/** 带正负号的金额，如 "+¥ 1,842.66" / "−¥ 312.80"。 */
function money(v: number): string {
  return `${v < 0 ? '−' : '+'}¥ ${fmt(Math.abs(v))}`
}

interface TileProps {
  k: string
  sub?: string
  v: ReactNode
  vClass?: string
  s: ReactNode
}
function Tile({ k, sub, v, vClass, s }: TileProps) {
  return (
    <div className="kpi">
      <div className="k">
        <span>{k}</span>
        {sub !== undefined && <span>{sub}</span>}
      </div>
      <div className={vClass ? `v ${vClass}` : 'v'}>{v}</div>
      <div className="s">{s}</div>
    </div>
  )
}

interface Props {
  state: StateView
  status: string
  simMode: boolean
}

/** 六格 KPI。已实现 与 浮动 分开两格显示（诚实性底线，不合并成「总收益」）。 */
export function KpiGrid({ state, status, simMode }: Props) {
  const s = state.snapshot
  const cfg = state.config
  const m = state.metrics
  const realized = Number(s.realized_pnl)
  const unrealized = Number(s.unrealized_pnl)
  const committed = Number(s.committed)
  const cap = Number(cfg.capital_cap)
  const capPct = cap > 0 ? Math.round((committed / cap) * 100) : 0
  const avg = Number(s.avg_cost)
  const sells = state.fills.filter((f) => f.side === 'sell')
  const wins = sells.filter((f) => f.realized_pnl !== undefined && Number(f.realized_pnl) > 0).length
  const winRate = sells.length > 0 ? Math.round((wins / sells.length) * 100) : 0
  const running = status === 'running'

  return (
    <div className="kpis rise d2">
      <Tile k="已实现盈亏" sub="累计" v={money(realized)} vClass={upDown(realized)} s={`${sells.length} 次套利`} />
      <Tile
        k="浮动盈亏"
        sub="持仓"
        v={money(unrealized)}
        vClass={unrealized === 0 ? undefined : upDown(unrealized)}
        s={
          <>
            底仓 {s.open_lots} 格 · 均价 {avg > 0 ? avg.toFixed(priceDecimals(avg)) : '—'}
          </>
        }
      />
      <Tile
        k="占用资金"
        sub="/ 上限"
        v={`¥ ${fmt(committed, 0)}`}
        s={
          <>
            上限 {fmt(cap, 0)} · <span className="accc">{capPct}%</span>
          </>
        }
      />
      <Tile
        k="网格套利"
        sub="胜率"
        v={
          <>
            {sells.length} <span style={{ fontSize: 12, color: 'var(--dim)' }}>次</span>
          </>
        }
        s={<span className={winRate >= 50 ? 'up' : undefined}>胜率 {winRate}%</span>}
      />
      <Tile
        k="夏普"
        sub={`总收益 ${fmt(Number(m.total_return) * 100)}%`}
        v={Number(m.sharpe).toFixed(2)}
        s={
          <>
            回撤 <span className="down">{(Number(m.max_drawdown) * 100).toFixed(1)}%</span>
          </>
        }
      />
      <Tile
        k="运行"
        sub={simMode ? 'sim' : 'replay'}
        v={running ? (simMode ? '跟盘' : '在跑') : '暂停'}
        vClass="accc"
        s={`${state.n_ticks} ticks`}
      />
    </div>
  )
}
