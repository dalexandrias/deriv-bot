import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, TrendingUp, Zap, History, BarChart2, ScrollText, Settings, CandlestickChart
} from 'lucide-react'

const nav = [
  { to: '/',          label: 'Overview',   icon: LayoutDashboard },
  { to: '/market',    label: 'Mercado',    icon: TrendingUp },
  { to: '/signals',   label: 'Sinais',     icon: Zap },
  { to: '/history',   label: 'Histórico',  icon: History },
  { to: '/candles',   label: 'Candles',    icon: CandlestickChart },
  { to: '/stats',     label: 'Stats',      icon: BarChart2 },
  { to: '/logs',      label: 'Logs',       icon: ScrollText },
  { to: '/settings',  label: 'Configurar', icon: Settings },
]

export function Sidebar() {
  return (
    <aside className="w-56 flex-none bg-lumen-surface border-r border-lumen-border flex flex-col h-screen sticky top-0">
      <div className="h-16 flex items-center px-5 border-b border-lumen-border flex-none">
        <img src="/lumen-logo.svg" alt="Lumen" className="h-7" />
      </div>
      <nav className="flex-1 overflow-y-auto py-3 px-2">
        {nav.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lumen-sm text-sm font-medium mb-0.5 transition-colors ` +
              (isActive
                ? 'bg-lumen-primary-soft text-lumen-primary'
                : 'text-lumen-body hover:bg-lumen-surface-2 hover:text-lumen-text')
            }
          >
            <Icon size={16} className="flex-none" />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
