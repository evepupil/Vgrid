import type { DcaBacktestResult } from '../api/client'
import { fmt, upDown } from '../utils/format'
import { EquityChart } from './EquityChart'

interface Props {
  result: DcaBacktestResult
}

function pct(v: string | null): string {
  if (v == null) return '—'
  const n = Number(v) * 100
  return `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`
}

/** 定投结果：定投特有 KPI 行（投入/XIRR/净利）+ 净值曲线（复用 EquityChart，关掉内嵌指标行）。 */
export function DcaResult({ result }: Props) {
  const m = result.metrics
  const investRet = Number(m.profit_rate_on_invested)
  const bhRet = Number(m.buy_hold_return)
  const profit = Number(m.profit)

  return (
    <div className="bt-result">
      <div className="kpis bt-kpis">
        <Kpi k="投入回报" v={pct(m.profit_rate_on_invested)} cls={upDown(investRet)}>
          XIRR <span className={m.xirr ? upDown(Number(m.xirr)) : undefined}>{pct(m.xirr)}</span>
        </Kpi>
        <Kpi k="账户净利" v={`¥ ${fmt(profit, 0)}`} cls={upDown(profit)}>
          末权益 ¥ {fmt(Number(m.final_equity), 0)}
        </Kpi>
        <Kpi k="累计投入" v={`¥ ${fmt(Number(m.invested_amount), 0)}`}>
          买入 {m.n_buys} · 跳过 {m.skipped_count}
        </Kpi>
        <Kpi k="买入持有" v={pct(m.buy_hold_return)} cls={upDown(bhRet)}>
          回撤 <span className="down">−{(Number(m.max_drawdown) * 100).toFixed(1)}%</span>
        </Kpi>
      </div>

      <EquityChart
        equity={result.equity_curve}
        buyHold={result.buy_hold_curve}
        drawdown={result.drawdown_curve}
        showStats={false}
        legendText="实线=定投 · 绿虚=买入持有"
      />

      <div className="scanrow bt-warn">
        ⚠ 手续费累计 ¥ {fmt(Number(m.total_fee), 2)}。投入回报未扣买入费（费单列）；账户净利已含费。
        XIRR 按每笔投入时间贴现的真实年化，和买入持有的自然日年化口径不同，别直接相较。
      </div>
    </div>
  )
}

function Kpi({
  k,
  v,
  cls,
  children,
}: {
  k: string
  v: string
  cls?: string
  children: React.ReactNode
}) {
  return (
    <div className="kpi">
      <div className="k">
        <span>{k}</span>
      </div>
      <div className={cls ? `v ${cls}` : 'v'}>{v}</div>
      <div className="s">{children}</div>
    </div>
  )
}
