import { useMemo } from 'react'
import type uPlot from 'uplot'
import type { CompareRow } from '../api/client'
import { type Mode, useMode } from '../mode/context'
import { Uplot } from './Uplot'

// 网格随模式取强调色；定投固定蓝；买入持有绿虚线。三线一眼分得开。
const ACCENT: Record<Mode, string> = { live: '#f5b62c', sim: '#2ad4c4' }
const DCA_COLOR = '#7c9cff'

function cssVar(name: string, fallback: string): string {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

function styleFor(
  name: string,
  accent: string,
  down: string,
): { stroke: string; dash?: number[] } {
  if (name === '定投') return { stroke: DCA_COLOR }
  if (name === '买入持有') return { stroke: down, dash: [3, 3] }
  return { stroke: accent } // 网格
}

/** 三方净值叠加图：一策略一条线（网格实线 / 定投蓝 / 买入持有绿虚）+ 底部图例。 */
export function CompareChart({ rows }: { rows: CompareRow[] }) {
  const { mode } = useMode()
  const acc = ACCENT[mode]
  const down = cssVar('--down', '#25c281')
  const faint = cssVar('--faint', '#59616d')
  const hair = cssVar('--hair', 'rgba(233,231,224,.09)')

  const data = useMemo<uPlot.AlignedData>(() => {
    const base = rows[0]?.curve ?? []
    const xs = base.map((p) => new Date(p.ts).getTime() / 1000)
    return [xs, ...rows.map((r) => r.curve.map((p) => Number(p.equity)))]
  }, [rows])

  const opts = useMemo<Omit<uPlot.Options, 'width' | 'height'>>(() => {
    const axis = (values?: uPlot.Axis['values']): uPlot.Axis => ({
      stroke: faint,
      grid: { stroke: hair, width: 1 },
      ticks: { stroke: hair, width: 1 },
      font: '10px "IBM Plex Mono", monospace',
      size: 42,
      values,
    })
    return {
      scales: { x: { time: true } },
      legend: { show: false },
      cursor: { show: true, points: { show: false }, y: false },
      axes: [
        { ...axis(), size: 26 },
        { ...axis((_u, s) => s.map((v) => `${(v / 1000).toFixed(1)}k`)) },
      ],
      series: [
        {},
        ...rows.map((r) => {
          const st = styleFor(r.name, acc, down)
          return { label: r.name, stroke: st.stroke, width: 1.6, dash: st.dash, points: { show: false } }
        }),
      ],
    }
  }, [rows, acc, down, faint, hair])

  if (!rows.length || !rows[0]?.curve.length) {
    return (
      <div className="placeholder">
        <span className="ph-title">暂无对比数据</span>
      </div>
    )
  }

  return (
    <div className="cmp-chart">
      <Uplot opts={opts} data={data} height={240} />
      <div className="cmp-legend">
        {rows.map((r) => {
          const st = styleFor(r.name, acc, down)
          return (
            <span className="cmp-legend__item" key={r.name}>
              <i style={{ background: st.stroke, opacity: st.dash ? 0.7 : 1 }} />
              {r.name}
            </span>
          )
        })}
      </div>
    </div>
  )
}
