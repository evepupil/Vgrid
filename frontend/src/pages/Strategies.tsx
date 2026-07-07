import { Panel } from '../components/Panel'
import { Placeholder } from '../components/Placeholder'
import { SectionTitle } from '../components/SectionTitle'

/** 策略库。切 0 为骨架；列表将用 TanStack Table，表单用 react-hook-form。 */
export default function Strategies() {
  return (
    <div className="view">
      <SectionTitle title="策略库" en="Strategies" />
      <Panel className="rise d1">
        <Placeholder
          title="策略列表：区间/格数 · 模式 · 样本内夏普 · 状态 · 关联实例 · 部署"
          fr="FR-9（TanStack Table · 部署 FR-9.3）"
        />
      </Panel>
    </div>
  )
}
