import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getQuotes, getState, listRunners } from '../api/client'
import { EquityChart } from '../components/EquityChart'
import { GridLadder } from '../components/GridLadder'
import { InstrumentHeader } from '../components/InstrumentHeader'
import { KpiGrid } from '../components/KpiGrid'
import { LadderPanel } from '../components/LadderPanel'
import { Panel } from '../components/Panel'
import { Placeholder } from '../components/Placeholder'
import { RiskPanel } from '../components/RiskPanel'
import { useMode } from '../mode/context'

const KPIS = ['已实现盈亏', '浮动盈亏', '占用资金', '网格套利', '夏普', '运行'] as const
const POLL = 15000

/** 仪表盘：绑定一个运行实例 → 实时看盘。无实例则回退占位 + 策略预览阶梯。 */
export default function Dashboard() {
  const { mode } = useMode()
  const simMode = mode === 'sim'

  const runners = useQuery({ queryKey: ['runners', mode], queryFn: listRunners, refetchInterval: POLL })
  const list = runners.data ?? []
  // 总览页点卡片带 ?inst=<db> 进来时预选该实例；手动切换后以本地选择为准
  const [params] = useSearchParams()
  const fromUrl = params.get('inst')
  const [selDb, setSelDb] = useState<string | null>(null)
  const selected =
    list.find((r) => r.db_path === selDb) ??
    list.find((r) => r.db_path === fromUrl) ??
    list[0]

  const state = useQuery({
    queryKey: ['state', selected?.db_path],
    queryFn: () => getState(selected!.db_path),
    enabled: selected !== undefined,
    refetchInterval: POLL,
  })
  const quote = useQuery({
    queryKey: ['quote', selected?.symbol],
    queryFn: () => getQuotes([selected!.symbol]),
    enabled: selected !== undefined,
    refetchInterval: POLL,
  })

  const st = state.data
  const q = quote.data?.quotes[0]

  return (
    <div className="view">
      {selected ? (
        <InstrumentHeader
          instances={list}
          selectedDb={selected.db_path}
          onSelect={setSelDb}
          state={st}
          quote={q}
          simMode={simMode}
        />
      ) : (
        <Panel kick="标的看盘" en="INSTRUMENT" meta={simMode ? '模拟盘' : '实盘'} className="rise d1">
          <Placeholder title="无运行实例：用 vgrid paper run --db 启动一个" fr="FR-3.1 / FR-11.1" />
        </Panel>
      )}

      {selected && st ? (
        <KpiGrid state={st} status={selected.status} simMode={simMode} />
      ) : (
        <div className="kpis rise d2">
          {KPIS.map((k) => (
            <div className="kpi" key={k}>
              <div className="k">
                <span>{k}</span>
              </div>
              <div className="v faint">——</div>
            </div>
          ))}
        </div>
      )}

      <div className="hero">
        <Panel
          kick="网格阶梯"
          en="GRID LADDER"
          meta={st?.ladder ? '实例实时' : '策略预览'}
          className="rise d3"
        >
          {st?.ladder ? <GridLadder view={st.ladder} /> : <LadderPanel />}
        </Panel>
        <Panel kick="净值曲线" en="EQUITY" meta={st ? '实例实时' : '日线'} className="rise d4">
          {st ? (
            <EquityChart
              equity={st.equity_curve}
              buyHold={st.buy_hold_curve}
              drawdown={st.drawdown_curve}
              metrics={st.metrics}
            />
          ) : (
            <Placeholder title="净值 · 回撤 · 买入持有对照" fr="FR-5.1 / 5.2 / 5.3" />
          )}
        </Panel>
      </div>

      <div className="low">
        <Panel kick="成交流水" en="FILLS" className="rise d5">
          <Placeholder title="时间 · 方向 · 价格 · 份额 · 手续费 · 已实现" fr="FR-5.5（切3）" />
        </Panel>
        <Panel kick="风险敞口" en="RISK" meta="黑天鹅推演" className="rise d6">
          {selected && st ? (
            <RiskPanel state={st} simMode={simMode} />
          ) : (
            <Placeholder title="占用/上限 · 黑天鹅推演 · 已实现÷浮动分离" fr="FR-6 风控" />
          )}
        </Panel>
      </div>
    </div>
  )
}
