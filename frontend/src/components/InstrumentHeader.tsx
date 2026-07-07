import type { InstanceView, Quote, StateView } from '../api/client'
import { fmt, priceDecimals, signOf, upDown } from '../utils/format'
import { InstancePills } from './InstancePills'

interface Props {
  instances: InstanceView[]
  selectedDb: string
  onSelect: (db: string) => void
  state: StateView | undefined
  quote: Quote | undefined
  simMode: boolean
}

function spacingLabel(m: string): string {
  return m === 'geometric' ? '等比' : '等差'
}
function buildLabel(m: string): string {
  return m === 'zero' ? '零底仓' : '中枢建仓'
}

/** 标的头：切换器 + 代码/名称/标签 + 实时价/涨跌（现价来自 quote，含昨收算涨跌）。 */
export function InstrumentHeader({ instances, selectedDb, onSelect, state, quote, simMode }: Props) {
  const sel = instances.find((i) => i.db_path === selectedDb)
  const cfg = state?.config
  const symbol = cfg?.symbol ?? sel?.symbol ?? ''
  const name = quote?.name ?? sel?.name ?? symbol

  // 现价 + 涨跌：优先用 quote（带昨收），退化用 state 末价
  const price = quote ? Number(quote.price) : Number(state?.snapshot.last_price ?? 0)
  const prevClose = quote?.prev_close != null ? Number(quote.prev_close) : null
  const chg =
    quote?.change != null ? Number(quote.change) : prevClose !== null ? price - prevClose : null
  const pct =
    quote?.change_pct != null
      ? Number(quote.change_pct)
      : prevClose && prevClose !== 0
        ? ((price - prevClose) / prevClose) * 100
        : null
  const dp = priceDecimals(price || 1)
  const dir = upDown(chg ?? 0)

  const tag = cfg
    ? `${spacingLabel(cfg.spacing_mode)} · ${buildLabel(cfg.base_build_mode)} · ${cfg.grid_count} 格${simMode ? ' · 模拟' : ''}`
    : ''

  return (
    <>
      {instances.length > 1 && (
        <InstancePills instances={instances} selectedDb={selectedDb} onSelect={onSelect} />
      )}
      <div className="inst rise d1">
        <div className="inst__id">
          <span className="code">{symbol}</span>
          <span className="name">{name}</span>
          <span className="tag">{tag}</span>
        </div>
        <div className="inst__px">
          <span className={`p ${dir}`}>{price > 0 ? price.toFixed(dp) : '——'}</span>
          {chg !== null && pct !== null ? (
            <span className={`d ${dir}`}>
              {chg >= 0 ? '▲ +' : '▼ '}
              {fmt(chg, dp)} · {signOf(pct)}
              {fmt(pct)}%
            </span>
          ) : (
            <span className="d faint">行情待接入</span>
          )}
        </div>
        <div className="legend">
          <span className="chip">
            <span className="sw" style={{ background: 'var(--up)' }} />涨 / 买盘
          </span>
          <span className="chip">
            <span className="sw" style={{ background: 'var(--down)' }} />跌 / 卖盘
          </span>
          <span className="chip">
            <span className="sw" style={{ background: 'var(--acc)' }} />现价 / 仪表
          </span>
        </div>
      </div>
    </>
  )
}
