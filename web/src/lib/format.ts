// Wristband colours: one per event, stable across visits (hash of the id).
export const BANDS = ['orange', 'yellow', 'green', 'pink', 'blue', 'violet', 'red', 'teal'] as const
export type BandColor = (typeof BANDS)[number]

// Colours go round the palette in date order, so neighbouring events never share
// one; an event keeps its colour as later events are added. Ids not in the
// user's list (landing-page samples) fall back to a hash.
const assigned = new Map<string, BandColor>()
export function assignBands(events: { id: string; starts_at: string | null }[]) {
  assigned.clear()
  ;[...events]
    .sort((a, b) => (a.starts_at ?? '').localeCompare(b.starts_at ?? '') || a.id.localeCompare(b.id))
    .forEach((e, i) => assigned.set(e.id, BANDS[i % BANDS.length]))
}

export function bandFor(eventId: string): BandColor {
  const known = assigned.get(eventId)
  if (known) return known
  let h = 2166136261
  for (let i = 0; i < eventId.length; i++) h = Math.imul(h ^ eventId.charCodeAt(i), 16777619)
  return BANDS[Math.abs(h) % BANDS.length]
}

export const bandVar = (c: BandColor) => `var(--color-band-${c})`

const TZ = Intl.DateTimeFormat().resolvedOptions().timeZone

export function day(iso: string | null, tz?: string | null) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: tz || TZ })
}

export function dayYear(iso: string | null, tz?: string | null) {
  if (!iso) return ''
  const d = new Date(iso)
  const sameYear = d.getFullYear() === new Date().getFullYear()
  return d.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: sameYear ? undefined : 'numeric',
    timeZone: tz || TZ,
  })
}

export function time(iso: string | null, tz?: string | null) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', timeZone: tz || TZ })
}

export function ago(iso: string | null) {
  if (!iso) return 'never'
  const s = (Date.now() - new Date(iso).getTime()) / 1000
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.round(s / 60)} min ago`
  if (s < 86400) return `${Math.round(s / 3600)} h ago`
  return `${Math.round(s / 86400)} days ago`
}

export const n = (x: number | null | undefined) => (x ?? 0).toLocaleString('en-US')

export const plural = (count: number, one: string, many = `${one}s`) => `${n(count)} ${count === 1 ? one : many}`

export const CLUSTERS: Record<string, string> = {
  founder: 'Founder',
  investor: 'Investor',
  engineering: 'Engineer',
  product: 'Product',
  design: 'Design',
  gtm_growth: 'GTM and growth',
  other: 'Other',
  unknown: 'No bio',
}

/** A Partiful title for running text: hashtags and trailing separators removed. */
export function cleanTitle(title: string) {
  return title.replace(/\s*#\w+/g, '').replace(/\s*[-–—|·]\s*$/, '').replace(/\s+/g, ' ').trim() || title.trim()
}

/** Clean a Partiful title for a wristband: drop hashtags and collapse whitespace. */
export function bandTitle(title: string) {
  const t = title.replace(/#\w+/g, '').replace(/\s*[-–—|]\s*$/, '').replace(/\s+/g, ' ').trim()
  return t || title.trim()
}

export const ROLE_LABEL: Record<string, string> = {
  attended: 'Attended',
  hosting: 'Hosted',
  going: 'Going',
  waitlisted: 'Waitlisted',
  pending: 'Waiting for approval',
  maybe: 'Maybe',
  followed: 'Followed',
  saved: 'Saved',
  upcoming: 'Upcoming',
  unknown: 'Unknown',
}

/** Was the user in the room? Attended, or hosted and it has started. */
export function isMet(e: { role: string; starts_at: string | null }) {
  return e.role === 'attended' || (e.role === 'hosting' && !!e.starts_at && new Date(e.starts_at) <= new Date())
}

/** Ahead of the user: going, or hosting something that hasn't started. */
export function isComing(e: { role: string; starts_at: string | null }) {
  return e.role === 'going' || (e.role === 'hosting' && !!e.starts_at && new Date(e.starts_at) > new Date())
}
