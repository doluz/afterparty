import { RefreshCw } from 'lucide-react'
import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useMe, useRefreshData, useStartSync, useSync } from '../lib/api'
import { ago } from '../lib/format'

/** Where the data stands, and the way to refresh it. */
export function SyncBadge({ compact }: { compact?: boolean }) {
  const me = useMe()
  const sync = useSync(!!me.data?.partiful)
  const start = useStartSync()
  const refresh = useRefreshData()
  const run = sync.data
  const running = run?.status === 'running'

  // When a run finishes, everything derived from it is stale.
  const was = useRef(running)
  useEffect(() => {
    if (was.current && !running) void refresh()
    was.current = running
  }, [running, refresh])

  if (!me.data?.partiful) {
    return (
      <Link to="/onboarding?step=connect" className="btn btn-quiet h-9 px-3.5 text-caption">
        Connect Partiful
      </Link>
    )
  }
  if (me.data.partiful.token_error) {
    return (
      <Link to="/settings" className="btn btn-danger h-9 px-3.5 text-caption">
        Reconnect Partiful
      </Link>
    )
  }

  const label = running
    ? run.phase === 'guests' && run.events_total
      ? `Syncing ${run.events_done} of ${run.events_total}`
      : 'Syncing'
    : `Synced ${ago(me.data.partiful.last_sync_at)}`

  return (
    <button
      type="button"
      onClick={() => start.mutate(false)}
      disabled={running || start.isPending}
      className="flex h-9 items-center gap-2 rounded-full px-3 text-caption font-medium text-mute transition-colors hover:bg-white/5 hover:text-ink disabled:hover:bg-transparent"
      title="Sync with Partiful now"
    >
      <RefreshCw className={`size-3.5 ${running ? 'animate-spin text-uv' : ''}`} aria-hidden />
      <span className={compact && !running ? 'hidden sm:inline' : ''}>{label}</span>
    </button>
  )
}
