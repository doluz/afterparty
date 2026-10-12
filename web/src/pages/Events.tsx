import { ArrowLeft, ExternalLink, MapPin, Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ErrorNote, PageLoading } from '../components/bits'
import { PeopleList, PersonDrawer, PersonRow } from '../components/People'
import { ExportButton, SelectionBar, Toast, useExport, useSelection } from '../components/Selection'
import { PageTitle } from '../components/Shell'
import { Poster, Wristband } from '../components/Wristband'
import { useEvent, useEvents, type EventRow, type Guest } from '../lib/api'
import { CLUSTERS, ROLE_LABEL, bandFor, bandVar, cleanTitle, dayYear, isComing, isMet, n, plural, time } from '../lib/format'

const TABS: { key: 'past' | 'next' | 'other'; label: string; test: (e: EventRow) => boolean }[] = [
  { key: 'past', label: 'Attended', test: isMet },
  { key: 'next', label: 'Coming up', test: isComing },
  { key: 'other', label: 'Not admitted', test: (e) => !isMet(e) && !isComing(e) },
]

/** Guest rows rendered at a time: a 2,000-person block party stays fast. */
const PAGE = 150

function stub(e: EventRow) {
  if (e.guests) return plural(e.guests, 'person', 'people')
  if (e.hidden_rows) return 'List hidden'
  return ROLE_LABEL[e.role] ?? e.role
}

export function Events() {
  const events = useEvents()
  const [tab, setTab] = useState<(typeof TABS)[number]['key']>('past')
  if (events.isLoading) return <PageLoading />
  const all = events.data ?? []
  const current = TABS.find((t) => t.key === tab)!
  const list = all.filter(current.test)
  return (
    <div>
      <PageTitle sub="Every Partiful event on your account. Guest lists are read for the ones you were in.">Events</PageTitle>
      <div className="mb-6 inline-flex rounded-full border border-white/10 bg-white/[0.03] p-1" role="tablist" aria-label="Which events">
        {TABS.map((t) => {
          const count = all.filter(t.test).length
          const on = tab === t.key
          return (
            <button
              key={t.key}
              type="button"
              role="tab"
              aria-selected={on}
              onClick={() => setTab(t.key)}
              className={`h-9 rounded-full px-4 text-small font-semibold transition-colors ${on ? 'bg-ink text-night' : 'text-mute hover:text-ink'}`}
            >
              {t.label} <span className="ml-1 opacity-60">{count}</span>
            </button>
          )
        })}
      </div>
      {tab === 'other' && (
        <p className="mb-5 max-w-2xl text-small text-mute">
          You were waitlisted or are still waiting for approval. Partiful hides these guest lists until a host approves
          you.
        </p>
      )}
      {list.length === 0 ? (
        <p className="glass p-6 text-mute">Nothing here yet.</p>
      ) : (
        <ul className="space-y-3">
          {list.map((e) => (
            <li key={e.id}>
              <Link to={`/events/${e.id}`} className="flex items-center gap-3 transition-transform hover:-translate-y-0.5">
                <Poster eventId={e.id} title={e.title} src={e.image_url} className="size-14 shrink-0 sm:size-16" rounded="rounded-xl" compact />
                <Wristband
                  className="min-w-0 flex-1"
                  eventId={e.id}
                  title={e.title}
                  startsAt={e.starts_at}
                  timezone={e.timezone}
                  stub={stub(e)}
                  muted={tab === 'other'}
                />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function EventDetail() {
  const { id = '' } = useParams()
  const q = useEvent(id)
  const [search, setSearch] = useState('')
  const [reachable, setReachable] = useState(false)
  const [cluster, setCluster] = useState('')
  const [open, setOpen] = useState<Guest | null>(null)
  const [shown, setShown] = useState(PAGE)
  const sel = useSelection()
  const exp = useExport()

  const guests = useMemo(() => {
    const term = search.trim().toLowerCase()
    return (q.data?.guests ?? []).filter(
      (g) =>
        (!term || g.name.toLowerCase().includes(term) || (g.bio ?? '').toLowerCase().includes(term)) &&
        (!reachable || Object.keys(g.socials).length > 0 || !!g.linkedin_url) &&
        (!cluster || g.cluster === cluster),
    )
  }, [q.data, search, reachable, cluster])

  if (q.isLoading) return <PageLoading />
  if (q.error) return <ErrorNote error={q.error} />
  const { event: e, guests: all } = q.data!
  const clusters = Object.entries(
    all.reduce<Record<string, number>>((acc, g) => ((acc[g.cluster] = (acc[g.cluster] ?? 0) + 1), acc), {}),
  )
    .filter(([c]) => c !== 'unknown' && c !== 'other')
    .sort((a, b) => b[1] - a[1])
  const hiddenAll = all.length === 0 && e.hidden_rows > 0
  const visible = { event_id: e.id, q: search, cluster, social: reachable ? ('any' as const) : null }
  const exportSelection = () => exp.run(sel.all ? visible : { ids: [...sel.ids], event_id: e.id })
  const c = bandVar(bandFor(e.id))

  return (
    <div>
      <Link to="/events" className="mb-6 inline-flex items-center gap-1.5 text-small font-semibold text-mute hover:text-ink">
        <ArrowLeft className="size-4" aria-hidden /> Events
      </Link>

      <section className="relative">
        <div className="pointer-events-none absolute -inset-x-10 -top-16 h-72 opacity-40 blur-3xl" style={{ background: `radial-gradient(50% 60% at 20% 40%, ${c}, transparent 70%)` }} aria-hidden />
        <div className="relative flex flex-col gap-6 sm:flex-row sm:items-end">
          <Poster eventId={e.id} title={e.title} src={e.image_url} className="aspect-square w-40 shrink-0 sm:w-48" />
          <div className="min-w-0">
            <span className="rounded-full bg-white/10 px-2.5 py-1 text-caption font-semibold">
              {e.role === 'hosting' && isComing(e) ? 'Hosting' : (ROLE_LABEL[e.role] ?? e.role)}
            </span>
            <h1 className="mt-3 text-title">{cleanTitle(e.title)}</h1>
            <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-small text-mute">
              <span>
                {dayYear(e.starts_at, e.timezone)}, {time(e.starts_at, e.timezone)}
              </span>
              {e.location && (
                <span className="inline-flex items-center gap-1">
                  <MapPin className="size-3.5" aria-hidden /> {e.location}
                </span>
              )}
              <a href={`https://partiful.com/e/${e.id}`} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1 font-semibold text-ink hover:underline">
                Open on Partiful <ExternalLink className="size-3.5" aria-hidden />
              </a>
            </div>
          </div>
        </div>
      </section>

      {hiddenAll ? (
        <div className="glass mt-10 max-w-xl p-6">
          <h2 className="text-section">Guest list hidden</h2>
          <p className="mt-2 text-mute">
            The host hid the guest list. Partiful counts {n(e.hidden_rows)} guests but shows no names, to you or to
            Afterparty.
          </p>
        </div>
      ) : all.length === 0 ? (
        <p className="glass mt-10 p-6 text-mute">
          {e.guests_synced_at ? 'Nobody else on this guest list.' : 'Afterparty reads guest lists only for events you attended, hosted or are going to.'}
        </p>
      ) : (
        <section className="mt-10">
          <div className="flex flex-wrap items-center gap-2">
            <label className="relative min-w-56 flex-1 sm:max-w-xs">
              <span className="sr-only">Search guests</span>
              <Search className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-faint" aria-hidden />
              <input value={search} onChange={(x) => setSearch(x.target.value)} placeholder="Search name or bio" className="field pl-10" />
            </label>
            <button type="button" className="chip" aria-pressed={reachable} onClick={() => setReachable((v) => !v)}>
              Has a social
            </button>
            {clusters.slice(0, 5).map(([k, count]) => (
              <button key={k} type="button" className="chip" aria-pressed={cluster === k} onClick={() => setCluster(cluster === k ? '' : k)}>
                {CLUSTERS[k] ?? k} <span className="opacity-60">{count}</span>
              </button>
            ))}
          </div>
          <div className="mb-3 mt-5 flex flex-wrap items-center justify-between gap-3">
            <p className="text-small text-mute">
              {guests.length === all.length ? plural(all.length, 'person', 'people') : `${n(guests.length)} of ${n(all.length)} people`}
              {e.hidden_rows > 0 && `, plus ${n(e.hidden_rows)} hidden by Partiful`}
            </p>
            <ExportButton
              label={guests.length === all.length ? 'Export guest list' : `Export ${n(guests.length)}`}
              busy={exp.busy}
              onClick={() => exp.run(visible)}
            />
          </div>
          {guests.length ? (
            <>
              <PeopleList>
                {guests.slice(0, shown).map((g) => (
                  <PersonRow
                    key={g.person_id}
                    p={g}
                    onOpen={(x) => setOpen(x as Guest)}
                    selected={sel.has(g.person_id)}
                    onSelect={sel.toggle}
                  />
                ))}
              </PeopleList>
              {guests.length > shown && (
                <div className="mt-6 flex justify-center">
                  <button type="button" className="btn btn-quiet" onClick={() => setShown((v) => v + PAGE)}>
                    Show more ({n(guests.length - shown)} left)
                  </button>
                </div>
              )}
            </>
          ) : (
            <p className="glass p-6 text-mute">Nobody matches. Remove a filter to see more people.</p>
          )}
        </section>
      )}
      <SelectionBar sel={sel} total={guests.length} busy={exp.busy} onExport={exportSelection} />
      <Toast text={exp.note} />
      <PersonDrawer p={open} onClose={() => setOpen(null)} />
    </div>
  )
}
