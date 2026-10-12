import { Loader2 } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import type { FollowUp } from '../lib/api'

const AVATAR_HUES = [270, 320, 20, 190, 145, 45, 0, 220]

/** Photo when Partiful has one; otherwise initials on a gradient keyed to the name. */
export function Avatar({ name, src, size = 40 }: { name: string; src?: string | null; size?: number }) {
  const [broken, setBroken] = useState(false)
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join('')
  let h = 0
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0
  const hue = AVATAR_HUES[h % AVATAR_HUES.length]
  return src && !broken ? (
    <img
      src={src}
      alt=""
      loading="lazy"
      onError={() => setBroken(true)}
      className="shrink-0 rounded-full bg-dusk-2 object-cover ring-1 ring-white/10"
      style={{ width: size, height: size }}
    />
  ) : (
    <span
      aria-hidden
      className="flex shrink-0 items-center justify-center rounded-full font-display font-semibold text-white/90 ring-1 ring-white/10"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.38,
        background: `linear-gradient(140deg, hsl(${hue} 70% 46%), hsl(${(hue + 40) % 360} 60% 20%))`,
      }}
    >
      {initials || '?'}
    </span>
  )
}

const ICONS: Record<string, ReactNode> = {
  linkedin: (
    <path d="M4.98 3.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5ZM3 9.75h4v11H3v-11Zm6.5 0h3.8v1.6h.06c.53-1 1.83-2.06 3.77-2.06 4.03 0 4.77 2.6 4.77 6v5.46h-4v-4.84c0-1.15-.02-2.64-1.6-2.64-1.62 0-1.86 1.26-1.86 2.56v4.92H9.5v-11Z" />
  ),
  twitter: (
    <path d="M17.7 3h3.07l-6.7 7.67L22 21h-6.18l-4.84-6.33L5.44 21H2.37l7.17-8.2L2 3h6.33l4.37 5.79L17.7 3Zm-1.08 16.2h1.7L7.46 4.72H5.64L16.62 19.2Z" />
  ),
  instagram: (
    <path d="M12 7.2a4.8 4.8 0 1 0 0 9.6 4.8 4.8 0 0 0 0-9.6Zm0 7.9a3.1 3.1 0 1 1 0-6.2 3.1 3.1 0 0 1 0 6.2Zm6.1-8.1a1.12 1.12 0 1 1-2.24 0 1.12 1.12 0 0 1 2.24 0ZM12 3.6c2.73 0 3.05.01 4.13.06 2.77.13 4.07 1.44 4.2 4.2.05 1.08.06 1.4.06 4.14s-.01 3.05-.06 4.13c-.13 2.76-1.43 4.07-4.2 4.2-1.08.05-1.4.06-4.13.06s-3.06-.01-4.14-.06c-2.77-.13-4.07-1.45-4.2-4.2C3.6 15.05 3.6 14.73 3.6 12s.01-3.06.06-4.14c.13-2.76 1.43-4.07 4.2-4.2C8.94 3.61 9.27 3.6 12 3.6ZM12 2c-2.72 0-3.06.01-4.13.06-3.63.17-5.65 2.18-5.82 5.82C2.01 8.94 2 9.28 2 12s.01 3.06.06 4.13c.17 3.63 2.18 5.65 5.82 5.82 1.07.04 1.41.05 4.12.05s3.06-.01 4.13-.06c3.63-.17 5.65-2.18 5.82-5.82.05-1.06.06-1.4.06-4.12s-.01-3.06-.06-4.13c-.17-3.62-2.18-5.65-5.82-5.82C15.06 2.01 14.72 2 12 2Z" />
  ),
}

const LABEL: Record<string, string> = {
  linkedin: 'LinkedIn',
  twitter: 'X',
  instagram: 'Instagram',
  tiktok: 'TikTok',
  snapchat: 'Snapchat',
  facebook: 'Facebook',
}
const ORDER = ['linkedin', 'twitter', 'instagram', 'tiktok', 'facebook', 'snapchat']

/** Links to a person's socials. LinkedIn from the bio counts too. Venmo is left out: it's not for networking. */
export function Socials({ socials, linkedin, size = 'md' }: { socials: Record<string, string>; linkedin?: string | null; size?: 'sm' | 'md' }) {
  const all = { ...socials }
  if (linkedin && !all.linkedin) all.linkedin = linkedin
  const links = ORDER.filter((k) => all[k]).map((k) => [k, all[k]] as const)
  if (!links.length) return null
  const box = size === 'sm' ? 'size-8' : 'size-10'
  return (
    <div className="flex items-center gap-0.5">
      {links.map(([k, url]) => (
        <a
          key={k}
          href={url}
          target="_blank"
          rel="noreferrer noopener"
          title={LABEL[k] ?? k}
          aria-label={LABEL[k] ?? k}
          onClick={(e) => e.stopPropagation()}
          className={`${box} flex items-center justify-center rounded-full text-mute transition-colors hover:bg-white/10 hover:text-ink`}
        >
          {ICONS[k] ? (
            <svg viewBox="0 0 24 24" className="size-[17px]" fill="currentColor" aria-hidden>
              {ICONS[k]}
            </svg>
          ) : (
            <span className="text-caption font-semibold">{(LABEL[k] ?? k).slice(0, 2)}</span>
          )}
        </a>
      ))}
    </div>
  )
}

const FOLLOW: { value: FollowUp; label: string; on: string }[] = [
  { value: 'todo', label: 'Follow up', on: 'bg-ink text-night' },
  { value: 'contacted', label: 'Contacted', on: 'bg-ok text-night' },
  { value: 'skip', label: 'Skip', on: 'bg-dusk-3 text-mute' },
]

/** Three-way follow-up toggle. Selecting the active option clears it. */
export function FollowUpToggle({ value, onChange, busy }: { value: FollowUp; onChange: (v: FollowUp) => void; busy?: boolean }) {
  return (
    <div
      role="group"
      aria-label="Follow-up"
      className="inline-flex rounded-full border border-white/10 bg-white/[0.03] p-0.5"
      onClick={(e) => e.stopPropagation()}
    >
      {FOLLOW.map((o) => {
        const on = value === o.value
        return (
          <button
            key={o.value}
            type="button"
            disabled={busy}
            aria-pressed={on}
            onClick={() => onChange(on ? 'none' : o.value)}
            className={`h-8 rounded-full px-3 text-caption font-semibold transition-colors ${on ? o.on : 'text-mute hover:text-ink'}`}
          >
            {o.label}
          </button>
        )
      })}
    </div>
  )
}

export function Spinner({ label }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-mute" role="status">
      <Loader2 className="size-4 animate-spin" aria-hidden />
      {label && <span className="text-small">{label}</span>}
    </span>
  )
}

export function PageLoading() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <Spinner label="Loading" />
    </div>
  )
}

export function ErrorNote({ error }: { error: unknown }) {
  if (!error) return null
  return (
    <p role="alert" className="rounded-2xl border border-danger/40 bg-danger/10 px-4 py-2.5 text-small text-danger">
      {(error as Error)?.message || 'Something went wrong.'}
    </p>
  )
}

export function Wordmark({ className = '' }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 font-display text-[1.375rem] font-bold tracking-[-0.03em] ${className}`}>
      <svg viewBox="0 0 64 64" className="size-7 drop-shadow-[0_0_10px_rgb(255_122_26/0.6)]" aria-hidden>
        <g transform="rotate(-18 32 32)">
          <rect x="5" y="20" width="54" height="24" rx="6" fill="var(--color-band-orange)" />
          <rect x="43" y="20" width="2" height="24" fill="var(--color-night)" />
          <circle cx="51" cy="32" r="3.2" fill="var(--color-night)" />
        </g>
      </svg>
      afterparty
    </span>
  )
}

/** Section heading with an optional right-side link or note. */
export function SectionHead({ title, aside }: { title: string; aside?: ReactNode }) {
  return (
    <div className="mb-4 flex items-end justify-between gap-4">
      <h2 className="text-section">{title}</h2>
      {aside && <div className="hidden text-small text-mute sm:block">{aside}</div>}
    </div>
  )
}
