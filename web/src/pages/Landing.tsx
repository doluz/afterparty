import { Link, Navigate } from 'react-router-dom'
import { Wordmark } from '../components/bits'
import { Wristband } from '../components/Wristband'
import { useAuth } from '../lib/auth'
import type { BandColor } from '../lib/format'

const DEMO: { id: string; title: string; at: string; stub: string; color: BandColor; tilt: number; ml: string; mr: string }[] = [
  { id: 'rooftop', title: 'Founders & Funders Rooftop', at: '2026-10-09T01:00:00Z', stub: '691 guests', color: 'orange', tilt: -3, ml: '0%', mr: '6%' },
  { id: 'after-dark', title: 'Demos After Dark', at: '2026-10-07T02:00:00Z', stub: '280 guests', color: 'violet', tilt: 2, ml: '8%', mr: '0%' },
  { id: 'oktoberfest', title: 'Oktoberfest Block Party', at: '2026-09-18T23:00:00Z', stub: '2,037 guests', color: 'teal', tilt: -1.2, ml: '3%', mr: '3%' },
  { id: 'voice-ai', title: 'Voice AI Night', at: '2026-09-11T01:30:00Z', stub: '140 guests', color: 'pink', tilt: 2.6, ml: '12%', mr: '10%' },
]

const STEPS = [
  { title: 'Ask for access', body: 'Sign in with Google or your email. Every account is approved by hand.' },
  { title: 'Connect Partiful', body: 'Add the Afterparty Connector to Chrome and select Connect. You stay signed in to Partiful as you are now.' },
  { title: 'Follow up', body: 'Everyone from the events you went to, with bios and socials, and who you keep running into.' },
]

export function Landing() {
  const { state } = useAuth()
  if (state.status === 'signedIn') return <Navigate to="/home" replace />
  return (
    <div className="min-h-dvh overflow-x-hidden">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5">
        <Wordmark />
        <Link to="/signin" className="btn btn-quiet h-10">
          Sign in
        </Link>
      </header>

      <main className="mx-auto max-w-6xl px-5">
        <section className="grid items-center gap-14 pb-20 pt-10 lg:grid-cols-[1.05fr_1fr] lg:pt-20">
          <div className="rise">
            <h1 className="text-[clamp(2.5rem,5.4vw,4rem)] leading-[1.02] tracking-[-0.04em]">
              Remember who was in the room.
            </h1>
            <p className="mt-6 max-w-lg text-[1.1875rem] leading-relaxed text-mute">
              Afterparty reads the guest lists of the Partiful events you went to and turns them into one list of
              people to follow up with: their bios, their LinkedIn, X and Instagram, and who you keep running into.
            </p>
            <div className="mt-9 flex flex-wrap items-center gap-4">
              <Link to="/signin" className="btn btn-primary h-12 px-7 text-body">
                Request access
              </Link>
              <span className="text-small text-faint">Invite-only. Free while in beta.</span>
            </div>
          </div>

          {/* Wristbands under blacklight: the product in one picture. */}
          <div aria-label="Example events" className="relative py-6">
            <div className="pointer-events-none absolute inset-0 -z-10 blur-3xl" aria-hidden style={{ background: 'radial-gradient(45% 55% at 50% 50%, rgb(139 108 255 / 0.35), transparent 70%)' }} />
            {DEMO.map((d, i) => (
              <div key={d.id} className="mb-4" style={{ transform: `rotate(${d.tilt}deg)`, marginLeft: d.ml, marginRight: d.mr }}>
                <Wristband
                  eventId={d.id}
                  title={d.title}
                  startsAt={d.at}
                  stub={d.stub}
                  color={d.color}
                  size="lg"
                  className="band-drop"
                  style={{ animationDelay: `${200 + i * 150}ms` }}
                />
              </div>
            ))}
          </div>
        </section>

        <section className="grid gap-4 pb-20 sm:grid-cols-3">
          {STEPS.map((s, i) => (
            <div key={s.title} className="glass p-6">
              <span className="flex size-9 items-center justify-center rounded-full bg-white/10 font-display text-body font-bold">{i + 1}</span>
              <h2 className="mt-5 text-section">{s.title}</h2>
              <p className="mt-2 text-mute">{s.body}</p>
            </div>
          ))}
        </section>

        <footer className="border-t border-white/[0.06] py-10 text-small text-faint">
          <p className="max-w-2xl">
            Afterparty only shows guest lists that Partiful already shows you. It never posts, RSVPs or messages anyone
            for you. Afterparty is not made by or affiliated with Partiful.{' '}
            <Link to="/how-it-works" className="font-semibold text-mute hover:text-ink">
              How it reads people
            </Link>
            {' · '}
            <Link to="/privacy" className="font-semibold text-mute hover:text-ink">
              Privacy
            </Link>
          </p>
        </footer>
      </main>
    </div>
  )
}
