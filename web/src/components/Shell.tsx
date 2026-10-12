import { CalendarDays, Home, Settings, Users } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { useEvents, useMe } from '../lib/api'
import { Avatar, Wordmark } from './bits'
import { SyncBadge } from './SyncBadge'

const NAV = [
  { to: '/home', label: 'Home', icon: Home },
  { to: '/people', label: 'People', icon: Users },
  { to: '/events', label: 'Events', icon: CalendarDays },
]

export function Shell() {
  const me = useMe()
  const events = useEvents()
  const items = NAV
  const name = me.data?.user.name || me.data?.user.email || ''

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-30 px-3 pt-3 sm:px-5">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-3 rounded-full border border-white/[0.07] bg-night/70 pl-4 pr-2 shadow-[0_10px_40px_-20px_rgb(0_0_0/0.8)] backdrop-blur-xl">
          <Link to="/home" aria-label="Afterparty home">
            <Wordmark className="text-xl" />
          </Link>
          <nav className="mx-auto hidden items-center gap-1 md:flex" aria-label="Main">
            {items.map((i) => (
              <NavLink
                key={i.to}
                to={i.to}
                className={({ isActive }) =>
                  `flex h-10 items-center rounded-full px-4 text-small font-semibold transition-colors ${
                    isActive ? 'bg-white/10 text-ink' : 'text-mute hover:text-ink'
                  }`
                }
              >
                {i.label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2 md:ml-0">
            <SyncBadge compact />
            <NavLink
              to="/settings"
              aria-label="Settings"
              className={({ isActive }) => `rounded-full p-0.5 transition-shadow ${isActive ? 'ring-2 ring-uv' : 'hover:ring-2 hover:ring-white/20'}`}
            >
              <Avatar name={name} src={me.data?.user.photo_url} size={38} />
            </NavLink>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl px-4 pb-32 pt-8 sm:px-6 md:pb-20 md:pt-12">
        {events.isLoading ? null : <Outlet />}
      </main>

      <nav
        aria-label="Main"
        className="fixed inset-x-3 bottom-3 z-30 flex rounded-full border border-white/[0.08] bg-night/80 p-1.5 shadow-[0_12px_40px_-12px_rgb(0_0_0/0.9)] backdrop-blur-xl md:hidden"
        style={{ marginBottom: 'env(safe-area-inset-bottom)' }}
      >
        {[...items, { to: '/settings', label: 'Settings', icon: Settings }].map((i) => (
          <NavLink
            key={i.to}
            to={i.to}
            className={({ isActive }) =>
              `flex flex-1 flex-col items-center gap-0.5 rounded-full py-2 text-[0.6875rem] font-semibold transition-colors ${
                isActive ? 'bg-white/10 text-ink' : 'text-faint'
              }`
            }
          >
            <i.icon className="size-5" aria-hidden />
            {i.label}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}

export function PageTitle({ children, sub, aside }: { children: ReactNode; sub?: ReactNode; aside?: ReactNode }) {
  return (
    <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-title">{children}</h1>
        {sub && <p className="mt-2 text-body text-mute">{sub}</p>}
      </div>
      {aside}
    </div>
  )
}
