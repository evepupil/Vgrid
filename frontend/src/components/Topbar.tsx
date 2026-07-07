import { useMode } from '../mode/context'
import { Clock } from './Clock'
import { ModeSwitch } from './ModeSwitch'

/** 顶栏：品牌 + 模式切换 + 市场状态 + 时钟 + 组合汇总。 */
export function Topbar() {
  const { mode } = useMode()
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

      {/* 组合汇总数据待 FR-2.1 接入 */}
      <div className="assets">
        <span className="lab">{mode === 'sim' ? '模拟总资产' : '总资产'}</span>
        <span className="val">
          ¥ <span className="faint">——</span>
        </span>
        <span className="chg faint">组合汇总 · 待接入</span>
      </div>
    </div>
  )
}
