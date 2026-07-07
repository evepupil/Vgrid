import { NavLink } from 'react-router-dom'
import {
  IconBacktest,
  IconDashboard,
  IconGear,
  IconPortfolio,
  IconStrategies,
  IconWatchlist,
} from './icons'
import type { ComponentType, SVGProps } from 'react'

interface NavEntry {
  to: string
  tip: string
  Icon: ComponentType<SVGProps<SVGSVGElement>>
  end: boolean
}

// 顺序与原型一致：总览 / 仪表盘 / 回测 / 策略库 / 关注
const NAV: NavEntry[] = [
  { to: '/portfolio', tip: '总览 · Portfolio', Icon: IconPortfolio, end: false },
  { to: '/', tip: '仪表盘 · Instrument', Icon: IconDashboard, end: true },
  { to: '/backtest', tip: '回测 · Backtest', Icon: IconBacktest, end: false },
  { to: '/strategies', tip: '策略库 · Strategies', Icon: IconStrategies, end: false },
  { to: '/watchlist', tip: '关注 · Watchlist（共享）', Icon: IconWatchlist, end: false },
]

export function Rail() {
  return (
    <aside className="rail">
      <div className="rail__logo">V</div>
      <nav className="nav">
        {NAV.map(({ to, tip, Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) => (isActive ? 'nav__item on' : 'nav__item')}
          >
            <Icon />
            <span className="tip">{tip}</span>
          </NavLink>
        ))}
      </nav>
      <div className="rail__foot">
        <IconGear />
      </div>
    </aside>
  )
}
