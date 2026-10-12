import { useQueryClient } from '@tanstack/react-query'
import { Check, Copy, Download, ExternalLink, Sparkles } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ErrorNote, Spinner, Wordmark } from '../components/bits'
import { Wristband } from '../components/Wristband'
import { api, useEvents, useMe, useStats, useSync, type SyncRun } from '../lib/api'
import { useAuth } from '../lib/auth'
import { connectorIds, extensionInstalled, isChromium, isMobile, readPartifulSession } from '../lib/extension'
import { BANDS, bandVar, n, plural } from '../lib/format'

const STEPS = ['How it works', 'Add the connector', 'Connect Partiful', 'First sync'] as const

export function Onboarding() {
  const me = useMe()
  const [params] = useSearchParams()
  const [step, setStep] = useState<number | null>(null)

  // Resume where the account is: reconnecting skips the intro, connected means straight to the sync.
  useEffect(() => {
    if (step !== null || !me.data) return
    if (params.get('step') === 'connect') setStep(1)
    else setStep(me.data.partiful ? 3 : 0)
  }, [me.data, step, params])

  useEffect(() => {
    window.scrollTo({ top: 0 })
  }, [step])

  if (step === null) return null

  return (
    <div className="flex min-h-dvh flex-col px-5 py-5">
      <Wordmark className="self-start" />
      <div className="mx-auto w-full max-w-xl flex-1 py-10 sm:py-14">
        {/* Progress as four small wristbands: one lights up per step. */}
        <ol className="mb-8 grid grid-cols-4 gap-2" aria-label="Setup steps">
          {STEPS.map((label, i) => {
            const c = bandVar(BANDS[[0, 5, 3, 7][i]])
            const lit = i <= step
            return (
              <li key={label} aria-current={i === step ? 'step' : undefined}>
                <span
                  className="tyvek block h-2 rounded-full transition-all duration-500"
                  style={{ background: lit ? c : 'rgb(255 255 255 / 0.08)', boxShadow: lit ? `0 0 16px -2px ${c}` : undefined }}
                />
                <span className={`mt-2 hidden text-caption font-semibold sm:block ${i === step ? 'text-ink' : 'text-faint'}`}>{label}</span>
              </li>
            )
          })}
        </ol>
        <div key={step} className="glass rise p-7 sm:p-9">
          {step === 0 && <Welcome onNext={() => setStep(1)} />}
          {step === 1 && <Install onNext={() => setStep(2)} />}
          {step === 2 && <Connect onNext={() => setStep(3)} />}
          {step === 3 && <FirstSync />}
        </div>
      </div>
    </div>
  )
}

function Welcome({ onNext }: { onNext: () => void }) {
  const me = useMe()
  const first = (me.data?.user.name ?? '').split(' ')[0]
  return (
    <section>
      <h1 className="text-title">{first ? `You're in, ${first}.` : "You're in."}</h1>
      <p className="mt-3 text-mute">
        Setup takes about two minutes. You add a small Chrome extension, connect your Partiful account, and Afterparty
        reads the guest lists of your events.
      </p>
      <h2 className="mt-8 text-body font-semibold">What Afterparty keeps</h2>
      <ul className="mt-3 space-y-2.5 text-small text-mute">
        {[
          'The events on your Partiful home page, and the guest lists Partiful shows you for events you attended, hosted or are going to.',
          'For each guest: name, photo, bio and the socials they made visible to you.',
          'An encrypted Partiful sign-in token, so Afterparty can sync once a day. Disconnect any time in Settings.',
        ].map((t) => (
          <li key={t} className="flex gap-3">
            <Check className="mt-0.5 size-4 shrink-0 text-ok" aria-hidden />
            <span>{t}</span>
          </li>
        ))}
      </ul>
      <p className="mt-5 text-small text-mute">
        Afterparty never posts, RSVPs or messages anyone. You can delete everything from Settings. Details are on the{' '}
        <a href="/privacy" target="_blank" className="font-semibold text-ink hover:underline">
          privacy page
        </a>
        .
      </p>
      <button type="button" onClick={onNext} className="btn btn-primary mt-8 h-12 px-7 text-body">
        Start setup
      </button>
    </section>
  )
}

function Install({ onNext }: { onNext: () => void }) {
  const { config } = useAuth()
  const [installed, setInstalled] = useState(false)
  const [copied, setCopied] = useState(false)
  const dev = config.env === 'dev'

  // Poll for the connector so the step completes on its own once it's loaded.
  useEffect(() => {
    let live = true
    const check = async () => {
      const ok = await extensionInstalled(connectorIds(config))
      if (live) setInstalled(ok)
    }
    void check()
    const t = setInterval(check, 2000)
    return () => {
      live = false
      clearInterval(t)
    }
  }, [config])

  const copy = async () => {
    try {
      await navigator.clipboard.writeText('chrome://extensions')
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard blocked: the address is visible to copy by hand */
    }
  }

  if (isMobile()) {
    return (
      <section>
        <h1 className="text-title">Finish setup on a computer</h1>
        <p className="mt-3 text-mute">
          Connecting Partiful needs a Chrome extension, and phones cannot run extensions. Open {window.location.host} in
          Chrome on your laptop and sign in with the same account. After that, Afterparty works on this phone too.
        </p>
      </section>
    )
  }
  if (!isChromium()) {
    return (
      <section>
        <h1 className="text-title">Open Afterparty in Chrome</h1>
        <p className="mt-3 text-mute">
          The connector runs in Chrome and other Chromium browsers such as Arc, Brave and Edge. Open this page in one of
          those to continue. You need it only once, to connect.
        </p>
      </section>
    )
  }

  const store = config.connectorStoreUrl
  return (
    <section>
      <h1 className="text-title">Add the connector</h1>
      <p className="mt-3 text-mute">
        The Afterparty Connector reads your Partiful sign-in when you select Connect, and at no other time.
        {store ? ' Add it from the Chrome Web Store, then come back to this tab.' : ' It is not in the Chrome Web Store yet, so you add it by hand. It takes a minute.'}
      </p>
      {store ? (
        <div className="mt-7">
          <a href={store} target="_blank" rel="noreferrer noopener" className="btn btn-primary h-12 px-7 text-body">
            <Download className="size-4" aria-hidden /> Add to Chrome
          </a>
          <p className="mt-3 text-small text-mute">Chrome asks you to confirm. This page notices the connector on its own.</p>
        </div>
      ) : (
        <ol className="mt-7 space-y-5">
          <Step num={1}>
            <a href="/afterparty-extension.zip" download className="btn btn-quiet">
              <Download className="size-4" aria-hidden /> Download the connector
            </a>
            <p className="mt-2 text-small text-mute">Unzip it. You get a folder named afterparty-extension.</p>
          </Step>
          <Step num={2}>
            <p>
              Open{' '}
              <button type="button" onClick={copy} className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-2.5 py-0.5 font-semibold text-ink">
                chrome://extensions {copied ? <Check className="size-3.5 text-ok" /> : <Copy className="size-3.5" />}
              </button>{' '}
              in a new tab and turn on <span className="font-semibold text-ink">Developer mode</span>, top right.
            </p>
          </Step>
          <Step num={3}>
            <p>
              Select <span className="font-semibold text-ink">Load unpacked</span> and choose the afterparty-extension folder.
            </p>
          </Step>
        </ol>
      )}
      <div className="mt-8 flex flex-wrap items-center gap-4">
        <button type="button" onClick={onNext} disabled={!installed && !dev} className="btn btn-primary h-12 px-7 text-body">
          Continue
        </button>
        {installed ? (
          <span className="inline-flex items-center gap-2 font-semibold text-ok">
            <Check className="size-4" aria-hidden /> Connector found
          </span>
        ) : (
          <Spinner label={dev ? 'No connector. In local dev you can continue with demo data.' : 'Waiting for the connector'} />
        )}
      </div>
    </section>
  )
}

function Step({ num, children }: { num: number; children: ReactNode }) {
  return (
    <li className="grid grid-cols-[2.25rem_1fr] gap-3">
      <span className="flex size-8 items-center justify-center rounded-full bg-white/10 font-display font-bold">{num}</span>
      <div className="pt-1 text-mute">{children}</div>
    </li>
  )
}

function Connect({ onNext }: { onNext: () => void }) {
  const { config } = useAuth()
  const qc = useQueryClient()
  const [state, setState] = useState<'idle' | 'reading' | 'signedOut' | 'saving' | 'done'>('idle')
  const [name, setName] = useState<string | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const dev = config.env === 'dev'

  const finish = async (r: { displayName: string | null; sync: SyncRun }) => {
    qc.setQueryData(['sync'], r.sync)
    await qc.invalidateQueries({ queryKey: ['me'] })
    setName(r.displayName)
    setState('done')
    setTimeout(onNext, 900)
  }

  const connect = async () => {
    setError(null)
    setState('reading')
    const s = await readPartifulSession(connectorIds(config))
    if (!s.ok) {
      setError(new Error(s.error))
      setState('idle')
      return
    }
    if (!s.signedIn) {
      setState('signedOut')
      return
    }
    setState('saving')
    try {
      await finish(
        await api('/api/partiful/connect', {
          method: 'POST',
          body: JSON.stringify({ uid: s.uid, refreshToken: s.refreshToken, apiKey: s.apiKey, displayName: s.displayName }),
        }),
      )
    } catch (e) {
      setError(e as Error)
      setState('idle')
    }
  }

  const demo = async () => {
    setError(null)
    setState('saving')
    try {
      await finish(await api('/api/dev/demo-connect', { method: 'POST' }))
    } catch (e) {
      setError(e as Error)
      setState('idle')
    }
  }

  return (
    <section>
      <h1 className="text-title">Connect Partiful</h1>
      <p className="mt-3 text-mute">
        Sign in to partiful.com in this browser the way you usually do, then select Connect Partiful. The connector hands
        your Partiful session to Afterparty, which encrypts it before storing it.
      </p>

      {state === 'signedOut' && (
        <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.03] p-5">
          <p className="font-semibold">You are not signed in to Partiful in this browser.</p>
          <p className="mt-1 text-small text-mute">Open Partiful, sign in, then come back to this tab and select Connect Partiful again.</p>
          <a href="https://partiful.com/login" target="_blank" rel="noreferrer noopener" className="btn btn-quiet mt-4">
            Open Partiful <ExternalLink className="size-4" aria-hidden />
          </a>
        </div>
      )}

      <div className="mt-8 flex flex-wrap items-center gap-3">
        {state === 'done' ? (
          <span className="inline-flex items-center gap-2 text-body font-semibold text-ok">
            <Check className="size-5" aria-hidden /> Connected{name ? ` as ${name}` : ''}
          </span>
        ) : (
          <>
            <button type="button" onClick={connect} disabled={state === 'reading' || state === 'saving'} className="btn btn-primary h-12 px-7 text-body">
              {state === 'reading' ? <Spinner label="Reading your Partiful session" /> : state === 'saving' ? <Spinner label="Checking with Partiful" /> : 'Connect Partiful'}
            </button>
            {dev && (
              <button type="button" onClick={demo} disabled={state === 'saving'} className="btn btn-quiet h-12">
                <Sparkles className="size-4" aria-hidden /> Use demo data
              </button>
            )}
          </>
        )}
      </div>
      {dev && state !== 'done' && <p className="mt-3 text-caption text-faint">Local dev only: demo data is made-up people, so you can walk the flow without a real account.</p>}
      <div className="mt-4">
        <ErrorNote error={error} />
      </div>
    </section>
  )
}

function FirstSync() {
  const nav = useNavigate()
  const qc = useQueryClient()
  const sync = useSync()
  const run = sync.data
  const running = !run || run.status === 'running'
  const events = useEvents()
  const stats = useStats()

  // Bands drop in as each event's guest list lands.
  useEffect(() => {
    if (running) {
      const t = setInterval(() => {
        void qc.invalidateQueries({ queryKey: ['events'] })
        void qc.invalidateQueries({ queryKey: ['sync'] })
      }, 1500)
      return () => clearInterval(t)
    }
    void qc.invalidateQueries({ queryKey: ['events'] })
    void qc.invalidateQueries({ queryKey: ['stats'] })
  }, [running, qc])

  const done = (events.data ?? []).filter((e) => e.guests_synced_at && (e.guests ?? 0) > 0)
  const finish = async () => {
    await api('/api/me/onboarded', { method: 'POST' })
    await qc.invalidateQueries()
    nav('/home', { replace: true })
  }
  const pct = run?.events_total ? Math.round((100 * run.events_done) / run.events_total) : 0

  return (
    <section>
      <h1 className="text-title">{running ? 'Reading your guest lists' : 'Your wristbands'}</h1>
      <p className="mt-3 text-mute" aria-live="polite">
        {run?.status === 'error'
          ? run.error
          : running
            ? run?.phase === 'guests' && run.events_total
              ? `${run.events_done} of ${plural(run.events_total, 'event')} read.`
              : 'Finding your events.'
            : `${plural(done.length, 'event')} with guest lists. You met ${n(stats.data?.people)} people.`}
      </p>
      <div className="mt-5 h-1.5 overflow-hidden rounded-full bg-white/[0.07]">
        <div
          className="h-full rounded-full bg-uv shadow-[0_0_16px_rgb(139_108_255)] transition-[width] duration-700"
          style={{ width: `${running ? Math.max(pct, 4) : 100}%` }}
        />
      </div>

      <ul className="mt-7 space-y-2.5">
        {done.slice(0, 7).map((e, i) => (
          <li key={e.id} style={{ transform: `rotate(${((i % 3) - 1) * 0.7}deg)` }}>
            <Wristband className="band-drop" eventId={e.id} title={e.title} startsAt={e.starts_at} timezone={e.timezone} stub={plural(e.guests ?? 0, 'person', 'people')} />
          </li>
        ))}
      </ul>
      {done.length > 7 && <p className="mt-3 text-small text-mute">and {plural(done.length - 7, 'more event')}</p>}

      <button type="button" onClick={finish} disabled={running && done.length === 0} className="btn btn-primary mt-8 h-12 px-7 text-body">
        {running ? 'Continue while it syncs' : 'Open Afterparty'}
      </button>
    </section>
  )
}
