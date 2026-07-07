import { useMemo } from 'react'
import type uPlot from 'uplot'
import type { EquityPoint } from '../api/client'
import { useMode, type Mode } from '../mode/context'
import { fmt } from '../utils/format'
import { Uplot } from './Uplot'

// 强调色随模式（与 tokens.css 一致）。canvas 画不了 CSS 变量，显式给值。
const ACCENT: Record<Mode, string> = { live: '#f5b62c', sim: '#2ad4c4' }

function cssVar(name: string, fallback: string): string {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

function axis(stroke: string, grid: string): uPlot.Axis {
  return {
    stroke,
    grid: { stroke: grid, width: 1 },
    ticks: { stroke: grid, width: 1 },
    font: '10px "IBM Plex Mono", monospace',
    size: 42,
  }
}

function buildEqOpts(mode: Mode): Omit<uPlot.Options, 'width' | 'height'> {
  const acc = ACCENT[mode]
  const down = cssVar('--down', '#25c281')
  const faint = cssVar('--faint', '#59616d')
  const hair = cssVar('--hair', 'rgba(233,231,224,.09)')
  return {
    scales: { x: { time: true } },
    legend: { show: false },
    cursor: { show: true, points: { show: false }, y: false },
    axes: [
      { ...axis(faint, hair), size: 26 },
      { ...axis(faint, hair), values: (_u, s) => s.map((v) => `${(v / 1000).toFixed(1)}k`) },
    ],
    series: [
      {},
      { label: '净值', stroke: acc, width: 1.6, fill: `${acc}22`, points: { show: false } },
      { label: '买入持有', stroke: down, width: 1.2, dash: [3, 3], points: { show: false } },
    ],
  }
}

function buildDdOpts(): Omit<uPlot.Options, 'width' | 'height'> {
  const up = cssVar('--up', '#ff5257')
  const faint = cssVar('--faint', '#59616d')
  const hair = cssVar('--hair', 'rgba(233,231,224,.09)')
  return {
    scales: { x: { time: true } },
    legend: { show: false },
    cursor: { show: true, points: { show: false }, y: false },
    axes: [
      { ...axis(faint, hair), size: 26 },
      { ...axis(faint, hair), values: (_u, s) => s.map((v) => `${v.toFixed(0)}%`) },
    ],
    series: [
      {},
      { label: '回撤', stroke: up, width: 1.2, fill: 'rgba(255,82,87,.16)', points: { show: false } },
    ],
  }
}

function pct(v: string): string {
  const n = Number(v) * 100
  return `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`
}

function Stat({ k, v, cls }: { k: string; v: string; cls?: string }) {
  return (
    <div className="eq__stat">
      <div className="k">{k}</div>
      <div className={cls ? `v ${cls}` : 'v'}>{v}</div>
    </div>
  )
}

interface Metrics {
  total_return: string
  buy_hold_return: string
  max_drawdown: string
}

interface Props {
  equity: EquityPoint[]
  buyHold: { ts: string; equity: string }[]
  drawdown: { ts: string; drawdown: string }[]
  metrics: Metrics
}

/** 净值曲线：指标行 + 净值主图（网格实线 + 买入持有绿虚）+ 回撤条。看盘与回测共用。 */
export function EquityChart({ equity, buyHold, drawdown, metrics }: Props) {
  const { mode } = useMode()
  const eq = equity
  const bh = buyHold
  const dd = drawdown
  const m = metrics

  const eqData = useMemo<uPlot.AlignedData>(() => {
    const xs = eq.map((p) => new Date(p.ts).getTime() / 1000)
    return [xs, eq.map((p) => Number(p.equity)), bh.map((p) => Number(p.equity))]
  }, [eq, bh])
  const ddData = useMemo<uPlot.AlignedData>(() => {
    const xs = dd.map((p) => new Date(p.ts).getTime() / 1000)
    return [xs, dd.map((p) => Number(p.drawdown) * 100)]
  }, [dd])

  const eqOpts = useMemo(() => buildEqOpts(mode), [mode])
  const ddOpts = useMemo(() => buildDdOpts(), [])

  if (eq.length === 0) {
    return (
      <div className="placeholder">
        <span className="ph-title">该实例暂无净值数据</span>
      </div>
    )
  }

  const lastEq = Number(eq[eq.length - 1]?.equity ?? 0)
  const totalRet = Number(m.total_return)
  const bhRet = Number(m.buy_hold_return)

  return (
    <div className="eq">
      <div className="eq__row">
        <Stat k="末权益" v={`¥ ${fmt(lastEq, 0)}`} />
        <Stat k="总收益" v={pct(m.total_return)} cls={totalRet >= 0 ? 'up' : 'down'} />
        <Stat k="买入持有" v={pct(m.buy_hold_return)} cls={bhRet >= 0 ? 'up' : 'down'} />
        <Stat k="最大回撤" v={`−${(Number(m.max_drawdown) * 100).toFixed(1)}%`} cls="down" />
      </div>
      <Uplot opts={eqOpts} data={eqData} height={200} />
      <div className="eq__split">
        <span className="meta">回撤 DRAWDOWN</span>
        <span className="meta">实线=网格 · 绿虚=买入持有</span>
      </div>
      <Uplot opts={ddOpts} data={ddData} height={54} />
    </div>
  )
}
