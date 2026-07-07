import { useEffect, useState } from 'react'

function fmt(d: Date): string {
  return [d.getHours(), d.getMinutes(), d.getSeconds()]
    .map((n) => String(n).padStart(2, '0'))
    .join(':')
}

/** 顶栏时钟，每秒刷新。市场时段状态（交易中/午休/收盘）待 FR-11.2 接入。 */
export function Clock() {
  const [now, setNow] = useState<string>(() => fmt(new Date()))
  useEffect(() => {
    const id = setInterval(() => setNow(fmt(new Date())), 1000)
    return () => clearInterval(id)
  }, [])
  return <span>{now}</span>
}
