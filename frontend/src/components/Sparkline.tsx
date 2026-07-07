/** 迷你净值 sparkline：把一串权益点画成一条 SVG 折线，随模式取 --acc 描边。 */

interface Props {
  points: number[]
  stroke?: string // 缺省用当前模式强调色
  height?: number
}

const VIEW_W = 200

/** 把权益序列映射到 0..VIEW_W × 0..height 的折线 path。 */
function toPath(points: number[], height: number): string {
  if (points.length === 0) return ''
  if (points.length === 1) return `M0 ${height / 2} L${VIEW_W} ${height / 2}`
  const lo = Math.min(...points)
  const hi = Math.max(...points)
  const span = hi - lo || 1 // 全平时避免除零
  const pad = 3 // 上下留边，别贴顶贴底
  const usable = height - pad * 2
  const dx = VIEW_W / (points.length - 1)
  return points
    .map((p, i) => {
      const x = i * dx
      const y = pad + (1 - (p - lo) / span) * usable // 高值在上
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)}`
    })
    .join(' ')
}

export function Sparkline({ points, stroke = 'var(--acc)', height = 22 }: Props) {
  const d = toPath(points, height)
  return (
    <svg
      className="spark"
      viewBox={`0 0 ${VIEW_W} ${height}`}
      preserveAspectRatio="none"
      style={{ height }}
    >
      <path d={d} fill="none" stroke={stroke} strokeWidth={1.4} />
    </svg>
  )
}
