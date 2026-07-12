import { NavLink, Outlet } from 'react-router-dom'

import { getHealth } from '../../lib/api'
import { useAsync } from '../../lib/hooks'
import { AmbientBackground } from './AmbientBackground'

const NAV = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/validation', label: 'Validation', end: false },
  { to: '/insights', label: 'Model', end: false },
  { to: '/report', label: 'Report', end: false },
  { to: '/styleguide', label: 'Style Guide', end: false },
]

function HealthBadge() {
  const { data } = useAsync(getHealth, [])
  const ok = data?.database === 'connected'
  return (
    <div
      className="flex items-center gap-2"
      title={data ? `database ${data.database}` : 'checking'}
    >
      <span className={`h-2 w-2 rounded-full ${ok ? 'bg-gain' : 'bg-loss'}`} />
      <span className="font-mono text-[11px] text-muted">{data ? `API ${data.version}` : '…'}</span>
    </div>
  )
}

export function AppShell() {
  return (
    <div className="min-h-screen">
      <AmbientBackground />
      <header className="sticky top-0 z-10 border-b border-hairline bg-nav/80 backdrop-blur print:hidden">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-6">
            <span className="font-display text-sm font-semibold text-ink">Race Strategy</span>
            <nav className="flex items-center gap-1">
              {NAV.map((n) => (
                <NavLink
                  key={n.to}
                  to={n.to}
                  end={n.end}
                  className={({ isActive }) =>
                    `rounded-chip px-3 py-1.5 font-body text-sm transition-colors ${
                      isActive ? 'bg-surface-raised text-ink' : 'text-muted hover:text-ink'
                    }`
                  }
                >
                  {n.label}
                </NavLink>
              ))}
            </nav>
          </div>
          <HealthBadge />
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  )
}
