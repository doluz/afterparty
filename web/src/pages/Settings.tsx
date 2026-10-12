import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ErrorNote, Spinner } from '../components/bits'
import { PageTitle } from '../components/Shell'
import { api, authHeader, useMe, useStartSync, useSync } from '../lib/api'
import { useAuth } from '../lib/auth'
import { ago, dayYear, n } from '../lib/format'

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="glass p-6 sm:p-7">
      <h2 className="text-section">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  )
}

export function Settings() {
  const me = useMe()
  const sync = useSync()
  const start = useStartSync()
  const { signOut } = useAuth()
  const qc = useQueryClient()
  const nav = useNavigate()
  const [confirm, setConfirm] = useState('')
  const [copied, setCopied] = useState(false)

  const copyToken = async () => {
    const value = await authHeader()
    if (!value) return
    await navigator.clipboard.writeText(value)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const disconnect = useMutation({
    mutationFn: () => api('/api/partiful', { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['me'] }),
  })
  const del = useMutation({
    mutationFn: () => api('/api/me', { method: 'DELETE' }),
    onSuccess: async () => {
      await signOut()
      qc.clear()
      nav('/', { replace: true })
    },
  })

  const p = me.data?.partiful
  const run = sync.data
  const running = run?.status === 'running'

  return (
    <div>
      <PageTitle sub={me.data?.user.email}>Settings</PageTitle>
      <div className="space-y-4">

      <Card title="Partiful">
        {p ? (
          <>
            <p className="text-body">
              Connected as <span className="font-semibold">{p.display_name ?? 'your Partiful account'}</span>
            </p>
            <p className="mt-1 text-smallall text-mute">
              Since {dayYear(p.connected_at)}. Last synced {ago(p.last_sync_at)}. Afterparty syncs once a day.
            </p>
            {p.token_error && (
              <p className="mt-4 rounded-2xl border border-danger/40 bg-danger/10 px-4 py-2.5 text-smallall text-danger">
                Your Partiful session expired. Sign in to partiful.com in Chrome, then select Reconnect.
              </p>
            )}
            {run?.status === 'error' && !p.token_error && <p className="mt-3 text-small text-danger">Last sync failed: {run.error}</p>}
            {run?.status === 'ok' && run.error && <p className="mt-3 text-small text-mute">{run.error}</p>}
            <div className="mt-5 flex flex-wrap gap-2">
              <button type="button" className="btn btn-primary" disabled={running || start.isPending} onClick={() => start.mutate(true)}>
                {running ? <Spinner label={`Syncing ${run?.events_done ?? 0} of ${run?.events_total || '…'}`} /> : 'Sync everything now'}
              </button>
              <button type="button" className="btn btn-quiet" onClick={() => nav('/onboarding?step=connect')}>
                Reconnect
              </button>
              <button type="button" className="btn btn-danger" disabled={disconnect.isPending} onClick={() => disconnect.mutate()}>
                Disconnect
              </button>
            </div>
            <p className="mt-3 text-small text-faint">Disconnect deletes the stored Partiful session. Your events and notes stay.</p>
            {run?.status === 'ok' && <p className="mt-1 text-small text-faint">Last sync read {n(run.guests)} guests.</p>}
          </>
        ) : (
          <>
            <p className="text-mute">Partiful is not connected.</p>
            <button type="button" className="btn btn-primary mt-4" onClick={() => nav('/onboarding?step=connect')}>
              Connect Partiful
            </button>
          </>
        )}
      </Card>

      <Card title="Connector">
        <p className="text-small text-mute">
          You need the Chrome extension only to connect or reconnect Partiful. You can remove it after that.
        </p>
        <a href="/afterparty-extension.zip" download className="btn btn-quiet mt-4">
          Download the connector
        </a>
      </Card>

      <Card title="API access for agents">
        <p className="max-w-lg text-small text-mute">
          Scripts and AI agents can use the same JSON API as this app. Copy the token and give it to the agent as{' '}
          <code className="text-ink">AFTERPARTY_AUTH</code>, with this address as <code className="text-ink">AFTERPARTY_URL</code>.
          With Google or email sign-in, the token expires after one hour.
        </p>
        <button type="button" className="btn btn-quiet mt-4" onClick={() => void copyToken()}>
          {copied ? 'Copied' : 'Copy API token'}
        </button>
        <p className="mt-3 text-small text-faint">Anyone with the token can read and change your Afterparty data until it expires. Keep it private.</p>
      </Card>

      <Card title="Account">
        <p>{me.data?.user.email}</p>
        <button type="button" className="btn btn-quiet mt-4" onClick={() => signOut().then(() => nav('/'))}>
          Sign out
        </button>
      </Card>

      <Card title="Delete everything">
        <p className="max-w-lg text-small text-mute">
          Deletes your account, the Partiful connection, every synced event and guest, and your notes. This cannot be
          undone. Type <span className="font-semibold text-ink">delete</span> to confirm.
        </p>
        <div className="mt-4 flex max-w-md gap-2">
          <input value={confirm} onChange={(e) => setConfirm(e.target.value)} className="field" aria-label="Type delete to confirm" />
          <button type="button" className="btn btn-danger" disabled={confirm !== 'delete' || del.isPending} onClick={() => del.mutate()}>
            Delete my data
          </button>
        </div>
        <div className="mt-3">
          <ErrorNote error={del.error || disconnect.error || start.error} />
        </div>
      </Card>
      </div>
    </div>
  )
}
