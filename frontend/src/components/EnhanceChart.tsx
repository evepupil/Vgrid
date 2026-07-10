import { useMemo } from 'react'
import type uPlot from 'uplot'
import type { IncomeEnhanceResult } from '../api/client'
import { type Mode, useMode } from '../mode/context'
import { Uplot } from './Uplot'

// 增强走模式色实线，策略走灰虚线——一眼看出分红把曲线抬了多少。
const ACCENT: Record<Mode, string> = { live: '#f5b62c', sim: '#2ad4c4' }
const STRAT = '#9aa3ad'

function cssVar(name: string, fallback: string): string {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

/** 策略(价格口径) vs 分红再投增强 两条净值曲线叠加，x 轴取策略曲线交易日。 */
export function EnhanceChart({ result }: { result: IncomeEnhanceResult }) {
  const { mode } = useMode()
  const acc = ACCENT[mode]
  const faint = cssVar('--faint', '#59616d')
  const hair = cssVar('--hair', 'rgba(233,231,224,.09)')

  const { data, opts, hasData } = useMemo(() => {
    const strat = result.strategy_curve
    const enh = result.enhanced_curve
    const hasData = strat.length > 1
    const xs = strat.map((p) => new Date(p.day).getTime() / 1000)
    const enhAligned =
      enh.length === strat.length ? enh.map((p) => Number(p.value)) : strat.map(() => null)
    const data: uPlot.AlignedData = [xs, strat.map((p) => Number(p.value)), enhAligned]
    const axis = (values?: uPlot.Axis['values']): uPlot.Axis => ({
      stroke: faint,
      grid: { stroke: hair, width: 1 },
      ticks: { stroke: hair, width: 1 },
      font: '10px "IBM Plex Mono", monospace',
      size: 42,
      values,
    })
    const opts: Omit<uPlot.Options, 'width' | 'height'> = {
      scales: { x: { time: true } },
      legend: { show: false },
      cursor: { show: true, points: { show: false }, y: false },
      axes: [
        { ...axis(), size: 26 },
        { ...axis((_u, s) => s.map((v) => `${(v * 100).toFixed(0)}%`)) },
      ],
      series: [
        {},
        { label: '策略', stroke: STRAT, width: 1.6, dash: [4, 3], points: { show: false } },
        { label: '增强', stroke: acc, width: 1.8, points: { show: false } },
      ],
    }
    return { data, opts, hasData }
  }, [result, acc, faint, hair])

  if (!hasData) {
    return (
      <div className="placeholder">
        <span className="ph-title">无曲线数据</span>
      </div>
    )
  }

  return (
    <div className="inc-chart">
      <Uplot opts={opts} data={data} height={260} />
      <div className="cmp-legend">
        <span className="cmp-legend__item">
          <i style={{ background: STRAT, opacity: 0.7 }} />
          策略（价格口径）
        </span>
        <span className="cmp-legend__item">
          <i style={{ background: acc }} />
          分红再投增强
        </span>
      </div>
    </div>
  )
}
