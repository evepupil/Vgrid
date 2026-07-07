import type { BacktestResult } from '../api/client'
import { fmt, upDown } from '../utils/format'
import { EquityChart } from './EquityChart'
import { GridLadder } from './GridLadder'

interface Props {
  result: BacktestResult
}

function pct(v: string): string {
  const n = Number(v) * 100
  return `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`
}

/** 回测结果：指标行 + 净值/回撤/买入持有对照（复用 EquityChart）+ 期末阶梯 + 过拟合提示。 */
export function BacktestResult({ result }: Props) {
  const m = result.metrics
  const totalRet = Number(m.total_return)
  const bhRet = Number(m.buy_hold_return)
  const fee = Number(m.total_fee)
  const profit = Number(m.final_equity) - Number(m.initial_cash)
  const feeShare = profit > 0 ? ((fee / profit) * 100).toFixed(1) : '—'

  return (
    <div className="bt-result">
      <div className="kpis bt-kpis">
        <Kpi k="总收益" v={pct(m.total_return)} cls={upDown(totalRet)}>
          买入持有 <span className={upDown(bhRet)}>{pct(m.buy_hold_return)}</span>
        </Kpi>
        <Kpi k="年化 / 夏普" v={`${pct(m.annualized_return)} · ${Number(m.sharpe).toFixed(2)}`}>
          回撤 <span className="down">−{(Number(m.max_drawdown) * 100).toFixed(1)}%</span>
        </Kpi>
        <Kpi k="买/卖 · 胜率" v={`${m.n_buys}/${m.n_sells} · ${(Number(m.win_rate) * 100).toFixed(0)}%`}>
          盈亏比 {Number(m.profit_loss_ratio).toFixed(2)}
        </Kpi>
        <Kpi k="手续费" v={`¥ ${fmt(fee, 2)}`}>
          占利润 {feeShare}{feeShare === '—' ? '' : '%'}
        </Kpi>
      </div>

      <EquityChart
        equity={result.equity_curve}
        buyHold={result.buy_hold_curve}
        drawdown={result.drawdown_curve}
        metrics={m}
      />

      <div className="scanrow bt-warn">⚠ {result.overfit_note}</div>

      {result.end_ladder && (
        <div className="bt-ladder">
          <div className="eq__split">
            <span className="meta">期末阶梯 END LADDER</span>
            <span className="meta">回测结束时的网格状态</span>
          </div>
          <GridLadder view={result.end_ladder} />
        </div>
      )}
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
