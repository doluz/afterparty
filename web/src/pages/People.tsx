import { List, Network, Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ErrorNote, PageLoading, Spinner } from '../components/bits'
import { PeopleMap } from '../components/PeopleMap'
import { PeopleList, PersonDrawer, PersonRow } from '../components/People'
import { ExportButton, SelectionBar, Toast, useExport, useSelection } from '../components/Selection'
import { PageTitle } from '../components/Shell'
import { fetchPerson, usePeople, usePeopleMap, useStats, type PeopleFilters, type Person } from '../lib/api'
import { CLUSTERS, n } from '../lib/format'

const SOCIAL: { value: PeopleFilters['social']; label: string }[] = [
  { value: 'any', label: 'Any social' },
  { value: 'linkedin', label: 'LinkedIn' },
  { value: 'twitter', label: 'X' },
  { value: 'instagram', label: 'Instagram' },
]
const FOLLOW: { value: PeopleFilters['follow_up']; label: string }[] = [
  { value: 'none', label: 'Not marked' },
  { value: 'todo', label: 'To follow up' },
  { value: 'contacted', label: 'Contacted' },
  { value: 'skip', label: 'Skipped' },
]

function useDebounced<T>(value: T, ms = 250) {
  const [v, setV] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return v
}

export function People() {
  const [params, setParams] = useSearchParams()
  const view = params.get('view') === 'map' ? 'map' : 'list'
  const [q, setQ] = useState('')
  const [f, setF] = useState<Omit<PeopleFilters, 'q'>>({
    cluster: params.get('cluster') ?? '',
    social: (params.get('social') as PeopleFilters['social']) || '',
    follow_up: (params.get('follow_up') as PeopleFilters['follow_up']) || '',
    repeat: params.get('repeat') === '1',
  })
  const [noBio, setNoBio] = useState(false)
  const filters = { ...f, q: useDebounced(q) }
  const people = usePeople(filters)
  const map = usePeopleMap(filters)
  const stats = useStats()
  const sel = useSelection()
  const exp = useExport()
  const [open, setOpen] = useState<Person | null>(null)

  // A new filter is a new set of people: "all matching" no longer means the same thing.
  const key = JSON.stringify(filters)
  useEffect(() => {
    if (sel.all) sel.clear()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  const rows = people.data?.pages.flatMap((p) => p.people) ?? []
  const total = people.data?.pages[0]?.total ?? 0
  const clusters = Object.entries(stats.data?.clusters ?? {})
    .filter(([c]) => c !== 'unknown' && c !== 'other')
    .sort((a, b) => b[1] - a[1])
  const toggle = <K extends keyof typeof f>(k: K, value: (typeof f)[K]) =>
    setF((cur) => ({ ...cur, [k]: cur[k] === value ? (typeof value === 'boolean' ? false : '') : value }))
  const active = !!(q || f.cluster || f.social || f.follow_up || f.repeat)
  const setView = (v: 'list' | 'map') =>
    setParams(
      (p) => {
        if (v === 'map') p.set('view', 'map')
        else p.delete('view')
        return p
      },
      { replace: true },
    )

  const mapPeople = (map.data?.people ?? []).filter((p) => noBio || p.cluster !== 'unknown')
  const hiddenNoBio = (map.data?.people ?? []).filter((p) => p.cluster === 'unknown').length
  const exportSelection = () => exp.run(sel.all ? filters : { ids: [...sel.ids] })

  return (
    <div>
      <PageTitle
        sub={
          people.isFetching && !people.isFetchingNextPage ? (
            <Spinner />
          ) : (
            `${n(total)} ${active ? 'match' : 'people from the events you went to'}`
          )
        }
        aside={
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex rounded-full border border-white/10 bg-white/[0.03] p-1" role="tablist" aria-label="View">
              {(['list', 'map'] as const).map((v) => (
                <button
                  key={v}
                  type="button"
                  role="tab"
                  aria-selected={view === v}
                  onClick={() => setView(v)}
                  className={`flex h-9 items-center gap-1.5 rounded-full px-3.5 text-small font-semibold transition-colors ${view === v ? 'bg-ink text-night' : 'text-mute hover:text-ink'}`}
                >
                  {v === 'list' ? <List className="size-4" aria-hidden /> : <Network className="size-4" aria-hidden />}
                  {v === 'list' ? 'List' : 'Map'}
                </button>
              ))}
            </div>
            <ExportButton label={active ? `Export ${n(total)}` : 'Export all'} busy={exp.busy} onClick={() => exp.run(filters)} />
          </div>
        }
      >
        People
      </PageTitle>

      <div className="space-y-3">
        <label className="relative block max-w-lg">
          <span className="sr-only">Search people</span>
          <Search className="pointer-events-none absolute left-4 top-1/2 size-4 -translate-y-1/2 text-faint" aria-hidden />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search names and bios" className="field h-12 pl-10" />
        </label>
        <div className="scroll-row" role="group" aria-label="Filters">
          <button type="button" className="chip" aria-pressed={f.repeat} onClick={() => toggle('repeat', true)}>
            Met more than once
          </button>
          {SOCIAL.map((s) => (
            <button key={s.value} type="button" className="chip" aria-pressed={f.social === s.value} onClick={() => toggle('social', s.value)}>
              {s.label}
            </button>
          ))}
          {FOLLOW.map((s) => (
            <button key={s.value} type="button" className="chip" aria-pressed={f.follow_up === s.value} onClick={() => toggle('follow_up', s.value)}>
              {s.label}
            </button>
          ))}
        </div>
        {view === 'list' && (
          <div className="scroll-row" role="group" aria-label="Designation">
            {clusters.map(([c, count]) => (
              <button key={c} type="button" className="chip" aria-pressed={f.cluster === c} onClick={() => toggle('cluster', c)}>
                {CLUSTERS[c] ?? c} <span className="opacity-60">{n(count)}</span>
              </button>
            ))}
            <Link to="/how-it-works#designation" className="chip">
              How designations work
            </Link>
          </div>
        )}
      </div>

      <div className="mt-6">
        <ErrorNote error={people.error || map.error} />
        {view === 'map' ? (
          map.isLoading ? (
            <PageLoading />
          ) : (
            <>
              {hiddenNoBio > 0 && (
                <label className="mb-3 inline-flex cursor-pointer items-center gap-2 text-small text-mute">
                  <input type="checkbox" checked={noBio} onChange={(e) => setNoBio(e.target.checked)} className="size-4 accent-[var(--color-uv)]" />
                  Include {n(hiddenNoBio)} people with no bio
                </label>
              )}
              <PeopleMap
                people={mapPeople}
                onOpen={async (id) => setOpen(await fetchPerson(id))}
                onCluster={(c) => {
                  setF((cur) => ({ ...cur, cluster: c === 'unknown' || c === 'other' ? '' : c }))
                  setView('list')
                }}
              />
            </>
          )
        ) : people.isLoading ? (
          <PageLoading />
        ) : rows.length === 0 ? (
          <p className="glass p-6 text-mute">Nobody matches these filters. Remove a filter to see more people.</p>
        ) : (
          <>
            <div className="mb-2 flex items-center justify-between px-1 text-caption text-faint">
              <span>Tick people to export just them, or export everyone who matches.</span>
            </div>
            <PeopleList>
              {rows.map((p) => (
                <PersonRow key={p.person_id} p={p} onOpen={(x) => setOpen(x as Person)} selected={sel.has(p.person_id)} onSelect={sel.toggle} />
              ))}
            </PeopleList>
            {people.hasNextPage && (
              <div className="mt-6 flex justify-center">
                <button type="button" className="btn btn-quiet" onClick={() => people.fetchNextPage()} disabled={people.isFetchingNextPage}>
                  {people.isFetchingNextPage ? <Spinner /> : `Show more (${n(total - rows.length)} left)`}
                </button>
              </div>
            )}
          </>
        )}
      </div>
      <SelectionBar sel={sel} total={total} busy={exp.busy} onExport={exportSelection} />
      <Toast text={exp.note} />
      <PersonDrawer p={open} onClose={() => setOpen(null)} />
    </div>
  )
}
