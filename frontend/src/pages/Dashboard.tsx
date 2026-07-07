import { LadderPanel } from '../components/LadderPanel'
import { Panel } from '../components/Panel'
import { Placeholder } from '../components/Placeholder'
import { useMode } from '../mode/context'

// 六格 KPI（标签已知，值待接入）
const KPIS = ['已实现盈亏', '浮动盈亏', '占用资金', '网格套利', '夏普', '运行'] as const

/** 仪表盘（单实例看盘）。切 0 为骨架，各面板标注待接入的需求编号。 */
export default function Dashboard() {
  const { mode } = useMode()
  return (
    <div className="view">
      <Panel
        kick="标的看盘"
        en="INSTRUMENT"
        meta={mode === 'sim' ? '模拟盘' : '实盘'}
        className="rise d1"
      >
        <Placeholder title="标的切换器 · 实时价 · 涨跌" fr="FR-3.1 / FR-11.1" />
      </Panel>

      <div className="kpis rise d2">
        {KPIS.map((k) => (
          <div className="kpi" key={k}>
            <div className="k">{k}</div>
            <div className="v">——</div>
          </div>
        ))}
      </div>

      <div className="hero">
        <Panel kick="网格阶梯" en="GRID LADDER" meta="策略预览" className="rise d3">
          <LadderPanel />
        </Panel>
        <Panel kick="净值曲线" en="EQUITY" meta="日线" className="rise d4">
          <Placeholder title="净值 · 回撤 · 买入持有对照" fr="FR-5.1 / 5.2 / 5.3" />
        </Panel>
      </div>

      <div className="low">
        <Panel kick="成交流水" en="FILLS" className="rise d5">
          <Placeholder title="时间 · 方向 · 价格 · 份额 · 手续费 · 已实现" fr="FR-5.5" />
        </Panel>
        <Panel kick="风险敞口" en="RISK" meta="黑天鹅推演" className="rise d6">
          <Placeholder title="占用/上限 · 黑天鹅推演 · 已实现÷浮动分离" fr="FR-6 风控" />
        </Panel>
      </div>
    </div>
  )
}
