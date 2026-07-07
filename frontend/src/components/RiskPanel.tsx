import type { StateView } from '../api/client'
import { fmt, signOf, upDown } from '../utils/format'
import { Placeholder } from './Placeholder'

interface Props {
  state: StateView
  simMode: boolean
}

function k(v: number): string {
  return `${(v / 1000).toFixed(0)}k`
}
function dropLabel(pct: string): string {
  return `若 −${(Number(pct) * 100).toFixed(0)}%`
}

/** 风控 / 黑天鹅推演（FR-6）：占用条 + 逐档下跌推演 + 放大区/最大占用 + 已实现÷浮动说明。 */
export function RiskPanel({ state, simMode }: Props) {
  const risk = state.risk
  if (!risk) {
    return <Placeholder title="占用/上限 · 黑天鹅推演 · 已实现÷浮动分离" fr="FR-6 风控" />
  }
  const occ = risk.occupancy
  const ratio = Math.round(Number(occ.ratio_pct))
  const buffer = 100 - ratio
  const snap = state.snapshot

  const realized = Number(snap.realized_pnl)
  const floating = Number(snap.unrealized_pnl)

  return (
    <div className="risk">
      {/* 占用 / 硬上限 */}
      <div className="rk">
        <div className="rk__t">
          <span>占用资金 / 硬上限</span>
          <span className="accc">
            {ratio}% · 兜底 {buffer}%
          </span>
        </div>
        <div className="bar">
          <div className="fill" style={{ right: `${buffer}%` }} />
          <div className="txt">
            <span style={{ color: 'var(--acc)' }}>¥ {fmt(Number(occ.committed), 0)}</span>
            <span style={{ color: 'var(--faint)' }}>上限 ¥ {fmt(Number(occ.capital_cap), 0)}</span>
          </div>
        </div>
      </div>

      {/* 逐档下跌推演 */}
      <div className="swan">
        {risk.scenarios.map((s) => (
          <div key={s.drop_pct}>
            <span className="lab">{dropLabel(s.drop_pct)}</span>
            <span className="num down">−¥ {fmt(Number(s.position_loss), 0)}</span>
            <span className="lab" style={{ color: 'var(--faint)' }}>
              推演价 {Number(s.scenario_price).toFixed(3)}
            </span>
          </div>
        ))}
      </div>

      {/* 破下沿放大区 + 最大占用 */}
      <div className="swan swan2">
        <div>
          <span className="lab">跌破下沿</span>
          <span className={`num ${risk.amplification.enabled ? 'accc' : ''}`}>
            {risk.amplification.enabled ? '放大区' : '等距续接'}
          </span>
          <span className="lab" style={{ color: 'var(--faint)' }}>
            {risk.amplification.enabled
              ? `格距 ×${risk.amplification.down_spacing_factor} 减速`
              : `下沿 ${Number(risk.amplification.lower_price).toFixed(3)}`}
          </span>
        </div>
        <div>
          <span className="lab">最大占用</span>
          <span className="num">¥ {k(Number(risk.max_occupancy))}</span>
          <span className="lab" style={{ color: 'var(--faint)' }}>
            达上限即停买
          </span>
        </div>
      </div>

      {/* 已实现 vs 浮动 分离说明（FR-6.5） */}
      <div className="note">
        网格「利润」={' '}
        <span className="up">
          已实现套利 {signOf(realized)}
          {fmt(realized, 0)}
        </span>{' '}
        与{' '}
        <span className={upDown(floating)}>
          持仓浮{floating < 0 ? '亏' : '盈'} {fmt(Math.abs(floating), 0)}
        </span>{' '}
        分开记。当前 {Number(snap.open_lots)} 格底仓均价 {Number(snap.avg_cost).toFixed(3)}，靠上方卖单逐格解套；
        资金上限是黑天鹅硬兜底，占满即停止补仓。
        {simMode && <b style={{ color: 'var(--acc)' }}> 模拟盘不下真单，仅按成交价计得失。</b>}
      </div>
    </div>
  )
}
