import { Panel } from '../components/Panel'
import { Placeholder } from '../components/Placeholder'
import { SectionTitle } from '../components/SectionTitle'

/** 关注列表（实盘/模拟盘共享）。切 0 为骨架。 */
export default function Watchlist() {
  return (
    <div className="view">
      <SectionTitle
        title="关注列表"
        en="Watchlist"
        extra={<span className="chip acc">◈ 实盘 / 模拟盘 共享</span>}
      />
      <Panel className="rise d1">
        <Placeholder
          title="代码 · 名称 · 现价 · 涨跌 · 振幅 · 网格适配评分 · 60日走势"
          fr="FR-10（共享 · 适配评分 FR-10.3）"
        />
      </Panel>
    </div>
  )
}
