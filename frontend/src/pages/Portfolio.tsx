import { Panel } from '../components/Panel'
import { Placeholder } from '../components/Placeholder'
import { SectionTitle } from '../components/SectionTitle'
import { useMode } from '../mode/context'

/** 总览（组合，按当前模式）。切 0 为骨架。 */
export default function Portfolio() {
  const { mode } = useMode()
  return (
    <div className="view">
      <SectionTitle title={`投资组合 · ${mode === 'sim' ? '模拟盘' : '实盘'}`} en="Portfolio" />
      <Panel className="rise d1">
        <Placeholder title="总资产 · 日变动 · 已实现合计 · 浮动合计 · 占用/上限" fr="FR-2.1" />
      </Panel>

      <SectionTitle title="运行实例" en="Instances" />
      <Panel className="rise d2">
        <Placeholder
          title="每标的一卡：现价 · 已实现 · 浮动 · 占用 · 夏普/回撤 · 迷你净值"
          fr="FR-2.2 / 2.3"
        />
      </Panel>
    </div>
  )
}
