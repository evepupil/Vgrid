import { useMemo } from 'react'
import type uPlot from 'uplot'
import { type Mode, useMode } from '../mode/context'
import type { IncomeRow } from '../api/client'
import { Uplot } from './Uplot'

// 价格走模式色；另三条固定色，四线一眼分得开。
const ACCENT: Record<Mode, string> = { live: '#f5b62c', sim: '#2ad4c4' }
const CASH = '#7c9cff'
const REINVEST = '#25c281'
const NAV = '#9aa3ad'

function cssVar(name: string, fallback: string): string {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

/** 单只 ETF 四口径收益曲线叠加：价格(模式色实线) / 价+现分(蓝虚) / 价+分再投(绿实) / 累计净值(灰点)。

 * 四曲线以价格曲线的交易日为 x 轴；累计净值日期与交易日不一致时按 day 查表、
 * 缺口留 null（净值缺或日期对不上）。其余三条同 bars 日期，直接对齐。 */
export function IncomeChart({ row }: { row: IncomeRow }) {
  const { mode } = useMode()
  const acc = ACCENT[mode]
  const faint = cssVar('--faint', '#59616d')
  const hair = cssVar('--hair', 'rgba(233,231,224,.09)')

  const { data, opts, hasData } = useMemo(() => {
    const price = row.curves.price
    const hasData = price.length > 1
    const xs = price.map((p) => new Date(p.day).getTime() / 1000)
    const navMap = new Map(row.curves.acc_nav.map((p) => [p.day, p.value]))
    const cash = row.curves.cash_dividend
    const reinvest = row.curves.reinvest
    const cashAligned =
      cash.length === price.length ? cash.map((p) => Number(p.value)) : price.map(() => null)
    const reinvestAligned =
      reinvest.length === price.length
        ? reinvest.map((p) => Number(p.value))
        : price.map(() => null)
    const navAligned = price.map((p) => {
      const v = navMap.get(p.day)
      return v == null ? null : Number(v)
    })
    const data: uPlot.AlignedData = [
      xs,
      price.map((p) => Number(p.value)),
      cashAligned,
      reinvestAligned,
      navAligned,
    ]
    const styles = [
      { label: '价格', stroke: acc, dash: undefined as number[] | undefined },
      { label: '价+现分', stroke: CASH, dash: [4, 3] },
      { label: '价+分再投', stroke: REINVEST, dash: undefined },
      { label: '累计净值', stroke: NAV, dash: [1, 3] },
    ]
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
        ...styles.map((st) => ({
          label: st.label,
          stroke: st.stroke,
          width: 1.6,
          dash: st.dash,
          points: { show: false },
        })),
      ],
    }
    return { data, opts, hasData }
  }, [row, acc, faint, hair])

  if (!hasData) {
    return (
      <div className="placeholder">
        <span className="ph-title">该 ETF 无曲线数据</span>
      </div>
    )
  }

  return (
    <div className="inc-chart">
      <Uplot opts={opts} data={data} height={260} />
      <div className="cmp-legend">
        <span className="cmp-legend__item">
          <i style={{ background: acc }} />
          价格
        </span>
        <span className="cmp-legend__item">
          <i style={{ background: CASH, opacity: 0.7 }} />
          价+现分
        </span>
        <span className="cmp-legend__item">
          <i style={{ background: REINVEST }} />
          价+分再投
        </span>
        <span className="cmp-legend__item">
          <i style={{ background: NAV, opacity: 0.7 }} />
          累计净值
        </span>
      </div>
    </div>
  )
}
