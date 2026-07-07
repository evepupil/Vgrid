import type { LadderView } from '../api/client'

const LADDER_H = 560

/** 价格小数位：<2 元 4 位、<10 元 3 位、否则 2 位（跟原型一致）。 */
function decimals(price: number): number {
  if (price < 2) return 4
  if (price < 10) return 3
  return 2
}

interface Props {
  view: LadderView
}

/** 网格阶梯工程图：按视图数据把每条网格线定位渲染，叠加现价线 / 资金上限线 / 放大区。 */
export function GridLadder({ view }: Props) {
  const rungs = view.rungs
  const cur = Number(view.current_price)
  const cap = view.cap_price !== null ? Number(view.cap_price) : null

  const prices = rungs.map((r) => Number(r.price))
  const hi = Math.max(cur, ...prices)
  const lo = Math.min(cur, ...prices, cap ?? Number.POSITIVE_INFINITY)
  const span = hi - lo || 1
  const margin = span * 0.06
  const top = hi + margin
  const bot = lo - margin
  // 价格 → 阶梯内 y 像素
  const y = (p: number) => 10 + ((top - p) / (top - bot)) * (LADDER_H - 20)
  const dp = decimals(cur)

  const extPrices = rungs.filter((r) => r.depth > 0).map((r) => Number(r.price))
  const hasExt = extPrices.length > 0

  return (
    <div className="ladder">
      <div className="ladwrap">
        {rungs.map((r) => {
          const p = Number(r.price)
          const cls = `rung ${r.kind}${r.depth > 0 ? ' ext' : ''}`
          return (
            <div key={r.price} className={cls} style={{ top: `${y(p)}px` }}>
              {r.kind === 'sell' && <span className="ord">卖 {r.held_shares.toLocaleString()}</span>}
              {r.kind === 'buy' && <span className="ord">买 挂单</span>}
              {r.kind === 'capped' && <span className="ord">买 排队</span>}
              <span className="line" />
              <span className="px">{p.toFixed(dp)}</span>
            </div>
          )
        })}

        {cap !== null && (
          <div className="capline" style={{ top: `${y(cap)}px` }}>
            <span className="cl">资金上限 CAP</span>
          </div>
        )}

        {hasExt && (
          <span
            className="zone"
            style={{
              top: `${y(Math.max(...extPrices))}px`,
              height: `${y(Math.min(...extPrices)) - y(Math.max(...extPrices))}px`,
            }}
          >
            放大区
          </span>
        )}

        <div className="now" style={{ top: `${y(cur)}px` }}>
          <span className="tri" />
          <span className="nl" />
          <span className="flag">{cur.toFixed(dp)}</span>
        </div>
      </div>
    </div>
  )
}
