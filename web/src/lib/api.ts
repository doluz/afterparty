import {
  keepPreviousData,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { assignBands } from './format'

let getAuthHeader: (() => Promise<string | null>) | null = null
export function setTokenGetter(fn: (() => Promise<string | null>) | null) {
  getAuthHeader = fn
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const auth = getAuthHeader ? await getAuthHeader() : null
  if (auth) headers.set('Authorization', auth)
  if (init.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const res = await fetch(path, { ...init, headers })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = typeof body.detail === 'string' ? body.detail : (body.detail?.[0]?.msg ?? detail)
    } catch {
      /* not JSON */
    }
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}

// ------------------------------------------------------------------ types
export type SyncRun = {
  id: number
  trigger: string
  status: 'running' | 'ok' | 'error'
  phase: string | null
  events_total: number
  events_done: number
  guests: number
  error: string | null
  started_at: string
  finished_at: string | null
}

export type Me = {
  user: {
    id: number
    email: string
    name: string | null
    photo_url: string | null
    onboarded_at: string | null
  }
  partiful: {
    partiful_uid: string
    display_name: string | null
    connected_at: string
    last_sync_at: string | null
    token_error: string | null
  } | null
  sync: SyncRun | null
}

export type EventRow = {
  id: string
  title: string
  starts_at: string | null
  ends_at: string | null
  timezone: string | null
  location: string | null
  image_url: string | null
  role: string
  my_rsvp: string | null
  partiful_count: number | null
  guest_rows: number
  hidden_rows: number
  guests_synced_at: string | null
  guests?: number
  reachable?: number
}

export type FollowUp = 'none' | 'todo' | 'contacted' | 'skip'

export type Guest = {
  person_id: string
  name: string
  username: string | null
  avatar_url: string | null
  bio: string | null
  rsvp: string | null
  socials: Record<string, string>
  linkedin_url: string | null
  cluster: string
  follow_up: FollowUp
  note: string
  times_met: number
}

export type Person = Omit<Guest, 'rsvp'> & {
  last_met: string | null
  events: { id: string; title: string; starts_at: string | null }[]
}

export type Stats = {
  events_attended: number
  events_upcoming: number
  people: number
  reachable: number
  repeat: number
  contacted: number
  clusters: Record<string, number>
}


export type PeopleFilters = {
  q: string
  cluster: string
  social: '' | 'any' | 'linkedin' | 'twitter' | 'instagram'
  follow_up: '' | FollowUp
  repeat: boolean
}

// ------------------------------------------------------------------ hooks
export const useMe = (enabled = true) =>
  useQuery({ queryKey: ['me'], queryFn: () => api<Me>('/api/me'), enabled, retry: false })

export const useStats = () => useQuery({ queryKey: ['stats'], queryFn: () => api<Stats>('/api/stats') })

export const useEvents = () =>
  useQuery({
    queryKey: ['events'],
    queryFn: async () => {
      const rows = await api<EventRow[]>('/api/events')
      assignBands(rows) // before any band renders with this data
      return rows
    },
  })

export const useEvent = (id: string) =>
  useQuery({
    queryKey: ['event', id],
    queryFn: () => api<{ event: EventRow; guests: Guest[] }>(`/api/events/${encodeURIComponent(id)}`),
  })

const PAGE = 60
export const usePeople = (f: PeopleFilters) =>
  useInfiniteQuery({
    queryKey: ['people', f],
    initialPageParam: 0,
    placeholderData: keepPreviousData,
    queryFn: ({ pageParam }) => {
      const p = new URLSearchParams({ limit: String(PAGE), offset: String(pageParam) })
      if (f.q.trim()) p.set('q', f.q.trim())
      if (f.cluster) p.set('cluster', f.cluster)
      if (f.social) p.set('social', f.social)
      if (f.follow_up) p.set('follow_up', f.follow_up)
      if (f.repeat) p.set('repeat', 'true')
      return api<{ total: number; people: Person[] }>(`/api/people?${p}`)
    },
    getNextPageParam: (last, all) => {
      const loaded = all.reduce((n, pg) => n + pg.people.length, 0)
      return loaded < last.total ? loaded : undefined
    },
  })

/** Latest sync run; polls every 1.5 s while one is running. */
export const useSync = (enabled = true) =>
  useQuery({
    queryKey: ['sync'],
    queryFn: () => api<SyncRun | null>('/api/sync'),
    enabled,
    refetchInterval: (q) => (q.state.data?.status === 'running' ? 1500 : false),
    refetchIntervalInBackground: true, // only while a sync runs
  })

export function useStartSync() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (full: boolean) => api<SyncRun>('/api/sync', { method: 'POST', body: JSON.stringify({ full }) }),
    onSuccess: (run) => qc.setQueryData(['sync'], run),
  })
}

export function useSetFollowUp() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ personId, status, note }: { personId: string; status: FollowUp; note: string }) =>
      api(`/api/people/${encodeURIComponent(personId)}/follow-up`, {
        method: 'PUT',
        body: JSON.stringify({ status, note }),
      }),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['people'] })
      qc.invalidateQueries({ queryKey: ['people-map'] })
      qc.invalidateQueries({ queryKey: ['event'] })
      qc.invalidateQueries({ queryKey: ['stats'] })
    },
  })
}

/** Refresh everything derived from synced data (after a sync finishes). */
export function useRefreshData() {
  const qc = useQueryClient()
  return () =>
    Promise.all(
      ['me', 'stats', 'events', 'event', 'people', 'people-map'].map((k) => qc.invalidateQueries({ queryKey: [k] })),
    )
}

// ------------------------------------------------------------------ export, map, one person
export type ExportRequest = Partial<Omit<PeopleFilters, 'social' | 'follow_up'>> & {
  social?: PeopleFilters['social'] | null
  follow_up?: PeopleFilters['follow_up'] | null
  event_id?: string
  ids?: string[]
}

/** POST the filters (or a selection), get a CSV back, and save it. */
export async function exportPeople(req: ExportRequest): Promise<number> {
  const body = {
    ...req,
    social: req.social || null,
    follow_up: req.follow_up || null,
    cluster: req.cluster || '',
    q: req.q?.trim() || '',
  }
  const headers = new Headers({ 'Content-Type': 'application/json' })
  const auth = getAuthHeader ? await getAuthHeader() : null
  if (auth) headers.set('Authorization', auth)
  const res = await fetch('/api/people/export', { method: 'POST', headers, body: JSON.stringify(body) })
  if (!res.ok) throw new ApiError(res.status, 'Export failed. Try again.')
  const blob = await res.blob()
  const name = /filename="([^"]+)"/.exec(res.headers.get('content-disposition') ?? '')?.[1] ?? 'afterparty-people.csv'
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
  return Number(res.headers.get('x-afterparty-rows') ?? 0)
}

export type MapPerson = {
  person_id: string
  name: string
  cluster: string
  times_met: number
  reachable: boolean
  follow_up: FollowUp
  bio: string
}

export const usePeopleMap = (f: PeopleFilters) =>
  useQuery({
    queryKey: ['people-map', f],
    placeholderData: keepPreviousData,
    queryFn: () => {
      const p = new URLSearchParams()
      if (f.q.trim()) p.set('q', f.q.trim())
      if (f.social) p.set('social', f.social)
      if (f.follow_up) p.set('follow_up', f.follow_up)
      if (f.repeat) p.set('repeat', 'true')
      return api<{ total: number; people: MapPerson[] }>(`/api/people/map?${p}`)
    },
  })

export const fetchPerson = (id: string) => api<Person>(`/api/people/${encodeURIComponent(id)}`)
