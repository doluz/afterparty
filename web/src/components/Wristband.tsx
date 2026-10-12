import { useState, type CSSProperties, type ReactNode } from 'react'
import { bandFor, bandTitle, bandVar, day, type BandColor } from '../lib/format'

type Props = {
  eventId: string
  title: string
  startsAt?: string | null
  timezone?: string | null
  /** Right-hand stub: what this band is worth (guest count, status…). */
  stub?: ReactNode
  color?: BandColor
  muted?: boolean
  size?: 'sm' | 'md' | 'lg'
  glow?: boolean
  className?: string
  style?: CSSProperties
}

/** An event as a Tyvek wristband under blacklight: title printed along the band,
 *  a perforated tear line, a stub with the date, and the glow the band throws. */
export function Wristband({ eventId, title, startsAt, timezone, stub, color, muted, size = 'md', glow = true, className = '', style }: Props) {
  const c = bandVar(color ?? bandFor(eventId))
  const pad = size === 'lg' ? 'px-5 py-3.5' : size === 'sm' ? 'px-3 py-1.5' : 'px-4 py-2.5'
  const type = size === 'lg' ? 'text-[clamp(1.3rem,2.4vw,1.8rem)]' : size === 'sm' ? 'text-base' : 'text-[1.3rem]'
  return (
    <div
      className={`tyvek relative flex items-stretch overflow-hidden rounded-md text-night ${className}`}
      style={{
        backgroundColor: muted ? 'var(--color-dusk-3)' : c,
        color: muted ? 'var(--color-mute)' : undefined,
        boxShadow: muted || !glow ? undefined : `0 0 0 1px rgb(255 255 255 / 0.12) inset, 0 10px 32px -10px ${c}, 0 0 48px -18px ${c}`,
        ...style,
      }}
    >
      <div className={`flex min-w-0 flex-1 items-center ${pad}`}>
        <span className={`font-band line-clamp-2 font-extrabold uppercase leading-[0.92] tracking-[0.01em] ${type}`}>
          {bandTitle(title) || 'Untitled event'}
        </span>
      </div>
      {(startsAt || stub) && (
        <div
          className={`flex shrink-0 flex-col items-end justify-center border-l-2 border-dashed ${size === 'lg' ? 'w-36 px-4' : size === 'sm' ? 'w-20 px-2' : 'w-28 px-3'}`}
          style={{ borderColor: muted ? 'var(--color-line-2)' : 'rgb(15 11 20 / 0.32)' }}
        >
          {startsAt && (
            <span className={`font-band font-extrabold uppercase leading-none ${size === 'lg' ? 'text-2xl' : size === 'sm' ? 'text-sm' : 'text-lg'}`}>
              {day(startsAt, timezone)}
            </span>
          )}
          {stub && <span className="mt-1 text-right text-caption font-semibold opacity-75">{stub}</span>}
        </div>
      )}
      <div className={`flex shrink-0 items-center justify-center ${size === 'sm' ? 'w-5' : 'w-7'}`} aria-hidden>
        <span className="size-2.5 rounded-full" style={{ background: muted ? 'var(--color-line-2)' : 'rgb(15 11 20 / 0.5)' }} />
      </div>
    </div>
  )
}

/** A person's shared events as a stack of tiny glowing band tabs, one per event. */
export function BandTabs({ events, max = 8 }: { events: { id: string; title: string }[]; max?: number }) {
  const shown = events.slice(0, max)
  return (
    <div className="flex items-center gap-[3px]" aria-label={`At ${events.length} of your events`}>
      {shown.map((e) => {
        const c = bandVar(bandFor(e.id))
        return (
          <span
            key={e.id}
            title={bandTitle(e.title)}
            className="tyvek h-[18px] w-[7px] rounded-[2px]"
            style={{ backgroundColor: c, boxShadow: `0 0 10px -2px ${c}` }}
          />
        )
      })}
      {events.length > max && <span className="ml-1 text-caption text-mute">+{events.length - max}</span>}
    </div>
  )
}

/** Event art: Partiful's poster when there is one, else a gig poster printed in the band colour. */
export function Poster({ eventId, title, src, className = '', rounded = 'rounded-2xl', compact = false }: { eventId: string; title: string; src?: string | null; className?: string; rounded?: string; compact?: boolean }) {
  const [broken, setBroken] = useState(false)
  const c = bandVar(bandFor(eventId))
  const t = bandTitle(title) || 'Untitled'
  return (
    <div className={`relative overflow-hidden [container-type:inline-size] ${rounded} ${className}`} style={{ boxShadow: `0 14px 44px -18px ${c}` }}>
      {src && !broken ? (
        <img src={src} alt="" loading="lazy" onError={() => setBroken(true)} className="size-full object-cover" />
      ) : compact ? (
        <div className="tyvek flex size-full items-center justify-center" style={{ background: `radial-gradient(90% 90% at 30% 20%, color-mix(in oklab, ${c} 70%, white), ${c} 60%)` }}>
          <span className="font-band text-[1.6rem] font-black uppercase leading-none text-night/85">{t.charAt(0)}</span>
        </div>
      ) : (
        <div
          className="tyvek flex size-full flex-col justify-between p-4 text-night"
          style={{ background: `radial-gradient(120% 80% at 15% 0%, color-mix(in oklab, ${c} 65%, white) 0%, ${c} 55%, color-mix(in oklab, ${c} 70%, #0f0b14) 100%)` }}
        >
          <span className="font-band text-caption font-extrabold uppercase tracking-[0.12em] opacity-70">Afterparty</span>
          <span className="font-band line-clamp-4 text-[clamp(1.5rem,11cqi,2.4rem)] font-black uppercase leading-[0.86] tracking-[-0.005em]">{t}</span>
        </div>
      )}
      <div className="pointer-events-none absolute inset-0 rounded-[inherit] ring-1 ring-inset ring-white/15" />
    </div>
  )
}
