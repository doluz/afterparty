import { ExternalLink, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useSetFollowUp, type FollowUp, type Guest, type Person } from '../lib/api'
import { CLUSTERS, bandTitle } from '../lib/format'
import { Avatar, FollowUpToggle, Socials } from './bits'
import { BandTabs, Wristband } from './Wristband'

type Row = (Person | Guest) & { events?: Person['events'] }

const CLUSTER_TINT: Record<string, string> = {
  founder: 'text-band-orange',
  investor: 'text-band-pink',
  engineering: 'text-band-green',
  product: 'text-band-yellow',
  design: 'text-band-violet',
  gtm_growth: 'text-band-blue',
}

export function ClusterTag({ cluster }: { cluster: string }) {
  if (cluster === 'unknown' || cluster === 'other') return null
  return <span className={`text-caption font-semibold ${CLUSTER_TINT[cluster] ?? 'text-mute'}`}>{CLUSTERS[cluster] ?? cluster}</span>
}

/** The list a person lives in: one glass panel, hairline dividers. */
export function PeopleList({ children }: { children: React.ReactNode }) {
  return <ul className="glass divide-y divide-white/[0.06] overflow-hidden">{children}</ul>
}

export function PersonRow({
  p,
  onOpen,
  selected,
  onSelect,
}: {
  p: Row
  onOpen: (p: Row) => void
  /** When given, the row shows a checkbox for multi-select. */
  selected?: boolean
  onSelect?: (id: string, on: boolean) => void
}) {
  const set = useSetFollowUp()
  const [status, setStatus] = useState<FollowUp>(p.follow_up)
  useEffect(() => {
    setStatus(p.follow_up)
  }, [p.follow_up])
  const change = (v: FollowUp) => {
    setStatus(v)
    set.mutate({ personId: p.person_id, status: v, note: p.note })
  }
  return (
    <li
      className={`group grid cursor-pointer grid-cols-[auto_1fr] items-center gap-x-4 gap-y-3 px-4 py-4 transition-colors hover:bg-white/[0.03] sm:grid-cols-[auto_1fr_auto] sm:px-5 ${selected ? 'bg-uv/[0.08]' : ''}`}
      onClick={() => onOpen(p)}
    >
      <div className="flex items-center gap-3">
        {onSelect && (
          <label className="-m-2 flex p-2" onClick={(e) => e.stopPropagation()}>
            <span className="sr-only">Select {p.name}</span>
            <input
              type="checkbox"
              checked={!!selected}
              onChange={(e) => onSelect(p.person_id, e.target.checked)}
              className="size-[18px] cursor-pointer rounded accent-[var(--color-uv)]"
            />
          </label>
        )}
        <Avatar name={p.name} src={p.avatar_url} size={48} />
      </div>
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1">
          <button type="button" className="truncate text-left text-body font-semibold tracking-[-0.01em]" onClick={() => onOpen(p)}>
            {p.name}
          </button>
          <ClusterTag cluster={p.cluster} />
          {p.events && p.events.length > 1 && <BandTabs events={p.events} />}
          {!p.events && p.times_met > 1 && (
            <span className="rounded-full bg-uv/15 px-2 py-0.5 text-caption font-semibold text-uv">Met {p.times_met}×</span>
          )}
        </div>
        {p.bio && <p className="mt-0.5 line-clamp-1 text-small text-mute">{p.bio}</p>}
      </div>
      <div className="col-span-2 flex items-center justify-between gap-2 sm:col-span-1 sm:justify-end">
        <Socials socials={p.socials} linkedin={p.linkedin_url} size="sm" />
        <FollowUpToggle value={status} onChange={change} busy={set.isPending} />
      </div>
    </li>
  )
}

/** Compact card for horizontal rows on Home. */
export function PersonCard({ p, onOpen }: { p: Row; onOpen: (p: Row) => void }) {
  return (
    <button
      type="button"
      onClick={() => onOpen(p)}
      className="glass flex w-48 flex-col items-start gap-3 p-4 text-left transition-colors hover:bg-white/[0.06]"
    >
      <Avatar name={p.name} src={p.avatar_url} size={56} />
      <div className="min-w-0 self-stretch">
        <p className="truncate font-semibold tracking-[-0.01em]">{p.name}</p>
        <p className="mt-0.5 line-clamp-2 min-h-[2.6em] text-caption text-mute">{p.bio || 'No bio on Partiful'}</p>
      </div>
      <div className="flex items-center gap-2">
        {p.events && <BandTabs events={p.events} max={6} />}
        <span className="text-caption font-semibold text-ink">{p.times_met}×</span>
      </div>
    </button>
  )
}

export function PersonDrawer({ p, onClose }: { p: Row | null; onClose: () => void }) {
  const set = useSetFollowUp()
  const [note, setNote] = useState('')
  const [status, setStatus] = useState<FollowUp>('none')
  const savedNote = useRef('')
  const closeRef = useRef<HTMLButtonElement>(null)
  const panelRef = useRef<HTMLElement>(null)
  const onCloseRef = useRef(onClose)
  onCloseRef.current = onClose
  const pid = p?.person_id

  // Load the person once per opening. The drawer then owns its state: parent
  // re-renders (e.g. after a save refetches the list) must not reset it.
  useEffect(() => {
    if (!p) return
    setNote(p.note)
    setStatus(p.follow_up)
    savedNote.current = p.note
    closeRef.current?.focus()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pid])

  useEffect(() => {
    if (!pid) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCloseRef.current()
      if (e.key !== 'Tab' || !panelRef.current) return
      const focusable = panelRef.current.querySelectorAll<HTMLElement>('a[href], button:not([disabled]), textarea, input')
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        last?.focus()
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault()
        first?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [pid])

  if (!p) return null
  const save = (s: FollowUp, n: string) => {
    savedNote.current = n
    set.mutate({ personId: p.person_id, status: s, note: n })
  }
  const partiful = `https://partiful.com/u/${p.username ?? p.person_id}`

  return (
    <div className="fixed inset-0 z-50" role="dialog" aria-modal="true" aria-label={p.name}>
      {/* Backdrop: a mouse shortcut only. Keyboard and screen readers use the X button or Escape. */}
      <div aria-hidden className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <aside ref={panelRef} className="rise absolute inset-y-0 right-0 flex w-full max-w-[28rem] flex-col overflow-y-auto border-l border-white/[0.08] bg-dusk/95 px-6 pb-10 pt-6 shadow-2xl backdrop-blur-xl">
        <div className="flex justify-end">
          <button ref={closeRef} type="button" onClick={onClose} className="btn btn-quiet size-10 p-0" aria-label="Close">
            <X className="size-5" />
          </button>
        </div>
        <div className="-mt-4 flex flex-col items-center text-center">
          <Avatar name={p.name} src={p.avatar_url?.replace('w=96', 'w=320')} size={104} />
          <h2 className="mt-4 text-title">{p.name}</h2>
          <div className="mt-1 flex items-center gap-2">
            <ClusterTag cluster={p.cluster} />
            <Link to="/how-it-works#designation" onClick={onClose} className="text-caption text-faint hover:text-ink">
              {p.cluster === 'unknown' ? 'Why no designation?' : 'How is this decided?'}
            </Link>
          </div>
          {p.bio ? (
            <p className="mt-4 max-w-sm whitespace-pre-line text-body text-ink/85">{p.bio}</p>
          ) : (
            <p className="mt-4 text-small text-faint">No bio on Partiful.</p>
          )}
          <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
            <Socials socials={p.socials} linkedin={p.linkedin_url} />
            <a href={partiful} target="_blank" rel="noreferrer noopener" className="btn btn-quiet h-10 text-caption">
              Partiful profile <ExternalLink className="size-3.5" aria-hidden />
            </a>
          </div>
        </div>

        <section className="glass mt-8 p-5">
          <h3 className="text-body font-semibold">Follow-up</h3>
          <div className="mt-3">
            <FollowUpToggle
              value={status}
              busy={set.isPending}
              onChange={(v) => {
                setStatus(v)
                save(v, note)
              }}
            />
          </div>
          <label className="mt-5 block text-caption font-semibold text-mute" htmlFor="note">
            Note
          </label>
          <textarea
            id="note"
            rows={4}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            onBlur={() => note !== savedNote.current && save(status, note)}
            placeholder="What you talked about, what to send them"
            className="field mt-1.5 h-auto leading-relaxed"
          />
        </section>

        {p.events && p.events.length > 0 && (
          <section className="mt-8">
            <h3 className="text-body font-semibold">
              {p.events.length === 1 ? 'Where you met' : `Your ${p.events.length} events together`}
            </h3>
            <ul className="mt-3 space-y-2.5">
              {p.events.map((e) => (
                <li key={e.id}>
                  <Link to={`/events/${e.id}`} onClick={onClose} title={bandTitle(e.title)} className="block">
                    <Wristband eventId={e.id} title={e.title} startsAt={e.starts_at} size="sm" />
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        )}
      </aside>
    </div>
  )
}
