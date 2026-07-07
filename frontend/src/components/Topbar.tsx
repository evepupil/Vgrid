import { useQuery } from '@tanstack/react-query'
import { getPortfolioSummary } from '../api/client'
import { useMode } from '../mode/context'
import { fmt, upDown } from '../utils/format'
import { Clock } from './Clock'
import { ModeSwitch } from './ModeSwitch'

const POLL = 15000

/** 顶栏：品牌 + 模式切换 + 市场状态 + 时钟 + 组合汇总（总资产/已实现+浮动，FR-2.1）。 */
export function Topbar() {
  const { mode } = useMode()
  const summary = useQuery({
    queryKey: ['portfolio-summary'],
    queryFn: getPortfolioSummary,
    refetchInterval: POLL,
  })
  const s = summary.data
  const equity = s ? Number(s.total_equity) : null
  const netPnl = s ? Number(s.total_realized_pnl) + Number(s.total_unrealized_pnl) : null

  return (
    <div className="topbar">
      <div className="brand">
        <b>
          VGRID<span className="cur">▮</span>
        </b>
        <small>Grid Console</small>
      </div>

      <ModeSwitch />

      <div className="mkt">
        <span className="dot" /> 港股 · 交易中 <span className="faint">|</span> <Clock />
      </div>

      <div className="spacer" />

      <div className="assets">
        <span className="lab">{mode === 'sim' ? '模拟总资产' : '总资产'}</span>
        <span className="val">
          ¥ {equity !== null ? fmt(equity, 0) : <span className="faint">——</span>}
        </span>
        {netPnl !== null ? (
          <span className={`chg ${upDown(netPnl)}`}>
            {netPnl >= 0 ? '+' : '−'}¥ {fmt(Math.abs(netPnl), 0)} · 已实现+浮动
          </span>
        ) : (
          <span className="chg faint">组合汇总 · 待接入</span>
        )}
      </div>
    </div>
  )
}
