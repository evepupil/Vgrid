/** 导航图标：线性描边，随 currentColor 变色。 */
import type { SVGProps } from 'react'

type IconProps = SVGProps<SVGSVGElement>

const base: IconProps = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.6,
}

export function IconPortfolio(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <rect x="3" y="3" width="7" height="7" />
      <rect x="14" y="3" width="7" height="7" />
      <rect x="3" y="14" width="7" height="7" />
      <rect x="14" y="14" width="7" height="7" />
    </svg>
  )
}

export function IconDashboard(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M3 12h4l3-8 4 16 3-8h4" />
    </svg>
  )
}

export function IconBacktest(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M4 20V4M4 20h16M8 16l4-6 3 3 5-8" />
    </svg>
  )
}

export function IconStrategies(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <rect x="4" y="4" width="16" height="16" />
      <path d="M4 9h16M9 9v11" />
    </svg>
  )
}

export function IconCompare(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M12 3v18M5 7h14M5 7l-3 6h6zM19 7l-3 6h6z" />
    </svg>
  )
}

export function IconWatchlist(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M12 3l2.5 6H21l-5 4 2 7-6-4-6 4 2-7-5-4h6.5z" />
    </svg>
  )
}

export function IconGear(props: IconProps) {
  return (
    <svg {...base} width="18" strokeWidth={1.5} {...props}>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2" />
    </svg>
  )
}
