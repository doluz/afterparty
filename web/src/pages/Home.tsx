import { useState } from 'react'
import { Link } from 'react-router-dom'
import { PageLoading, SectionHead } from '../components/bits'
import { PersonCard, PersonDrawer } from '../components/People'
import { Poster, Wristband } from '../components/Wristband'
import { useEvents, useMe, usePeople, useStats, type Person } from '../lib/api'
import { cleanTitle, dayYear, isComing, isMet, n, plural, time } from '../lib/format'


function greeting() {
  const h = new Date().getHours()
  return h < 5 ? 'Still up' : h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening'
}

export function Home() {
  const me = useMe()
  const stats = useStats()
  const events = useEvents()
  const regulars = usePeople({ q: '', cluster: '', social: '', follow_up: '', repeat: true })
  const [open, setOpen] = useState<Person | null>(null)

  if (stats.isLoading || events.isLoading) return <PageLoading />
  const s = stats.data
  const past = (events.data ?? []).filter(isMet)
  const next = (events.data ?? []).filter(isComing).reverse()
  const people = regulars.data?.pages.flatMap((p) => p.people).slice(0, 10) ?? []
  const first = (me.data?.user.name ?? '').split(' ')[0]

  if (!s || (s.events_attended === 0 && next.length === 0)) {
    return (
      <div className="glass mx-auto max-w-xl p-8 text-center">
        <h1 className="text-title">No events yet</h1>
        <p className="mt-3 text-mute">
          Afterparty has not found a Partiful event you attended. After your next one, it shows up here with the
          next sync.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-14">
      <section className="rise">
        <p className="text-body text-mute">
          {greeting()}
          {first ? `, ${first}` : ''}.
        </p>
        <h1 className="mt-2 max-w-3xl text-display">
          You met {n(s.people)} people at {plural(s.events_attended, 'event')}.
        </h1>
        <div className="mt-6 flex flex-wrap gap-2">
          <Link to="/people?social=any" className="chip">
            <span className="font-semibold text-ink">{n(s.reachable)}</span> you can reach
          </Link>
          <Link to="/people?repeat=1" className="chip">
            <span className="font-semibold text-ink">{n(s.repeat)}</span> met more than once
          </Link>
          <Link to="/people?follow_up=contacted" className="chip">
            <span className="font-semibold text-ink">{n(s.contacted)}</span> contacted
          </Link>
        </div>
      </section>

      {next.length > 0 && (
        <section>
          <SectionHead title="Coming up" aside="See who is going before you get there" />
          <div className="scroll-row -mx-4 scroll-px-4 px-4 sm:mx-0 sm:scroll-px-0 sm:px-0">
            {next.map((e) => (
              <Link key={e.id} to={`/events/${e.id}`} className="group w-56">
                <Poster eventId={e.id} title={e.title} src={e.image_url} className="aspect-square w-56 transition-transform group-hover:-translate-y-0.5" />
                <p className="mt-3 line-clamp-2 font-semibold leading-snug tracking-[-0.01em]">{cleanTitle(e.title)}</p>
                <p className="mt-1 text-caption text-mute">
                  {dayYear(e.starts_at, e.timezone)}, {time(e.starts_at, e.timezone)}
                </p>
                <p className="text-caption text-mute">{e.role === 'hosting' ? 'You are hosting' : e.guests ? plural(e.guests, 'person', 'people') + ' going' : 'Guest list hidden'}</p>
              </Link>
            ))}
          </div>
        </section>
      )}

      {people.length > 0 && (
        <section>
          <div className="mb-4 flex items-end justify-between gap-4">
            <h2 className="text-section">People you keep running into</h2>
            <Link to="/people?repeat=1" className="shrink-0 text-small font-semibold hover:underline">See all {n(s.repeat)}</Link>
          </div>
          <div className="scroll-row -mx-4 scroll-px-4 px-4 sm:mx-0 sm:scroll-px-0 sm:px-0">
            {people.map((p) => (
              <PersonCard key={p.person_id} p={p} onOpen={(x) => setOpen(x as Person)} />
            ))}
          </div>
        </section>
      )}

      <section>
        <div className="mb-4 flex items-end justify-between gap-4">
          <h2 className="text-section">Your wristbands</h2>
          <Link to="/events" className="shrink-0 text-small font-semibold hover:underline">All events</Link>
        </div>
        <ul className="space-y-3">
          {past.slice(0, 6).map((e, i) => (
            <li key={e.id} style={{ transform: `rotate(${[-0.3, 0.2, -0.15, 0.25, -0.2, 0.1][i]}deg)` }}>
              <Link to={`/events/${e.id}`} className="block transition-transform hover:-translate-y-0.5">
                <Wristband
                  eventId={e.id}
                  title={e.title}
                  startsAt={e.starts_at}
                  timezone={e.timezone}
                  stub={e.guests ? plural(e.guests, 'person', 'people') : 'List hidden'}
                />
              </Link>
            </li>
          ))}
        </ul>
      </section>
      <PersonDrawer p={open} onClose={() => setOpen(null)} />
    </div>
  )
}
