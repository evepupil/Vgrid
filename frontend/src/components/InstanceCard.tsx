import type { InstanceView, Quote } from '../api/client'
import { fmt, priceDecimals, signOf, upDown } from '../utils/format'
import { Sparkline } from './Sparkline'

interface Props {
  inst: InstanceView
  quote: Quote | undefined
  simMode: boolean
  onClick: () => void
}

/** 千元档缩写：12345 → 「12k」。 */
function k(v: number): string {
  return `${(v / 1000).toFixed(0)}k`
}

/** 单实例卡（FR-2.2/2.3）：现价/涨跌 · 迷你净值 · 已实现/浮动/占用/夏普·回撤。点击进仪表盘。 */
export function InstanceCard({ inst, quote, simMode, onClick }: Props) {
  const price = quote ? Number(quote.price) : Number(inst.last_price ?? 0)
  const pct = quote?.change_pct != null ? Number(quote.change_pct) : null
  const dp = priceDecimals(price || 1)
  const dir = upDown(pct ?? 0)

  const realized = Number(inst.realized_pnl)
  const floating = Number(inst.unrealized_pnl)
  const used = Number(inst.committed)
  const cap = Number(inst.capital_cap)
  const sharpe = Number(inst.sharpe)
  const dd = Number(inst.max_drawdown)
  const spark = inst.equity_spark.map(Number)
  const running = inst.status === 'running'

  return (
    <div className="icard" onClick={onClick}>
      <section className="panel">
        <div className="top">
          <div className="nm">
            <b>{inst.name || inst.symbol}</b>
            <span>{inst.symbol}</span>
          </div>
          <div
            className="st"
            style={{
              color: running ? 'var(--acc)' : 'var(--faint)',
              borderColor: running ? 'var(--acc-glow)' : 'var(--hair)',
            }}
          >
            <span
              className="dot"
              style={{ width: 5, height: 5, background: running ? 'var(--acc)' : 'var(--faint)' }}
            />
            {running ? (simMode ? '跟盘' : '在跑') : '停歇'}
          </div>
        </div>

        <div className="px">
          <b className={dir}>{price > 0 ? price.toFixed(dp) : '——'}</b>
          {pct !== null ? (
            <span className={dir}>
              {pct >= 0 ? '▲ +' : '▼ '}
              {fmt(pct)}%
            </span>
          ) : (
            <span className="faint">行情待接入</span>
          )}
        </div>

        <div className="spark">
          <Sparkline points={spark} />
        </div>

        <div className="grid2">
          <div className="cell">
            <span className="l">已实现</span>
            <span className={`n ${upDown(realized)}`}>
              {signOf(realized)}¥{fmt(Math.abs(realized), 0)}
            </span>
          </div>
          <div className="cell">
            <span className="l">浮动</span>
            <span className={`n ${upDown(floating)}`}>
              {floating >= 0 ? '+' : '−'}¥{fmt(Math.abs(floating), 0)}
            </span>
          </div>
          <div className="cell">
            <span className="l">占用/上限</span>
            <span className="n">
              {k(used)}/{k(cap)}
            </span>
          </div>
          <div className="cell">
            <span className="l">夏普/回撤</span>
            <span className="n">
              {sharpe.toFixed(2)} · {fmt(dd * 100, 1)}%
            </span>
          </div>
        </div>
      </section>
    </div>
  )
}
