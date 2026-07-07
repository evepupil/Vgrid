import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { getPortfolioSummary, getQuotes, listRunners } from '../api/client'
import { InstanceCard } from '../components/InstanceCard'
import { Panel } from '../components/Panel'
import { Placeholder } from '../components/Placeholder'
import { PortfolioSummaryBar } from '../components/PortfolioSummaryBar'
import { SectionTitle } from '../components/SectionTitle'
import { useMode } from '../mode/context'

const POLL = 15000

/** 总览（组合，按当前模式）：汇总条 + 实例卡片（迷你净值），点卡进仪表盘。 */
export default function Portfolio() {
  const { mode } = useMode()
  const simMode = mode === 'sim'
  const nav = useNavigate()

  const summary = useQuery({
    queryKey: ['portfolio-summary'],
    queryFn: getPortfolioSummary,
    refetchInterval: POLL,
  })
  const runners = useQuery({ queryKey: ['runners'], queryFn: listRunners, refetchInterval: POLL })
  const list = runners.data ?? []

  const symbols = [...new Set(list.map((r) => r.symbol))]
  const quotes = useQuery({
    queryKey: ['quotes', symbols.join(',')],
    queryFn: () => getQuotes(symbols),
    enabled: symbols.length > 0,
    refetchInterval: POLL,
  })
  const quoteBy = new Map((quotes.data?.quotes ?? []).map((q) => [q.symbol, q]))

  return (
    <div className="view">
      <SectionTitle title={`投资组合 · ${simMode ? '模拟盘' : '实盘'}`} en="Portfolio" />
      <PortfolioSummaryBar summary={summary.data} simMode={simMode} />

      <SectionTitle title="运行实例" en={`${list.length} Instances`} />
      {list.length > 0 ? (
        <div className="insts rise d2">
          {list.map((inst) => (
            <InstanceCard
              key={inst.db_path}
              inst={inst}
              quote={quoteBy.get(inst.symbol)}
              simMode={simMode}
              onClick={() => nav(`/?inst=${encodeURIComponent(inst.db_path)}`)}
            />
          ))}
        </div>
      ) : (
        <Panel className="rise d2">
          <Placeholder title="无运行实例：用 vgrid paper run --db 启动一个" fr="FR-2.2 / 2.3" />
        </Panel>
      )}
    </div>
  )
}
