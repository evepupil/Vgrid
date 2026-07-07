import { useEffect, useRef } from 'react'
import uPlot from 'uplot'

interface Props {
  opts: Omit<uPlot.Options, 'width' | 'height'>
  data: uPlot.AlignedData
  height: number
}

/** uPlot 的 React 封装：opts（含颜色，随模式变）变化时重建，data 变化仅 setData，随容器宽度自适应。 */
export function Uplot({ opts, data, height }: Props) {
  const hostRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<uPlot | null>(null)
  const dataRef = useRef<uPlot.AlignedData>(data)
  dataRef.current = data

  useEffect(() => {
    const el = hostRef.current
    if (!el) return
    const width = el.clientWidth || 600
    const chart = new uPlot({ ...opts, width, height } as uPlot.Options, dataRef.current, el)
    chartRef.current = chart
    const ro = new ResizeObserver(() => {
      chart.setSize({ width: el.clientWidth || 600, height })
    })
    ro.observe(el)
    return () => {
      ro.disconnect()
      chart.destroy()
      chartRef.current = null
    }
  }, [opts, height])

  useEffect(() => {
    chartRef.current?.setData(data)
  }, [data])

  return <div ref={hostRef} className="uplot-host" />
}
