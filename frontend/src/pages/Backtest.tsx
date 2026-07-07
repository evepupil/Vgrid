import { Panel } from '../components/Panel'
import { Placeholder } from '../components/Placeholder'
import { SectionTitle } from '../components/SectionTitle'

/** 参数回测。切 0 为骨架；表单将用 react-hook-form 重建，图表用 uPlot。 */
export default function Backtest() {
  return (
    <div className="view">
      <SectionTitle title="参数回测" en="Backtest" />
      <div className="bt">
        <Panel kick="策略配置" en="CONFIG" className="rise d1">
          <Placeholder
            title="标的 · 区间 · 格数 · 每格金额 · 间距 · 建仓 · 上限 表单"
            fr="FR-7.1（react-hook-form）"
          />
        </Panel>
        <Panel kick="回测结果" en="RESULT" meta="样本内" className="rise d2">
          <Placeholder
            title="指标 · 净值 · 回撤 · 买入持有对照 · 期末阶梯"
            fr="FR-7.2 / 7.3 / 7.4（uPlot）"
          />
        </Panel>
      </div>
    </div>
  )
}
