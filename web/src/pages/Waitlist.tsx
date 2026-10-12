import { Navigate } from 'react-router-dom'
import { Wordmark } from '../components/bits'
import { Wristband } from '../components/Wristband'
import { useMe } from '../lib/api'
import { useAuth } from '../lib/auth'

export function Waitlist() {
  const { signOut } = useAuth()
  const me = useMe()
  if (me.data?.user.status === 'approved') return <Navigate to="/home" replace />
  const denied = me.data?.user.status === 'denied'
  return (
    <div className="flex min-h-dvh flex-col px-5 py-5">
      <Wordmark className="self-start" />
      <main className="mx-auto flex w-full max-w-lg flex-1 flex-col justify-center py-12">
        <div className="-rotate-2 px-6">
          <Wristband eventId="door" title={denied ? 'Not on the list' : 'On the list'} stub={denied ? 'Closed' : 'Pending'} color="violet" muted={denied} size="lg" className="band-drop" />
        </div>
        <div className="glass rise mt-10 p-7 sm:p-9">
          <h1 className="text-title">{denied ? 'Not this time' : 'You are on the list'}</h1>
          <p className="mt-3 text-mute">
            {denied
              ? 'Your request for access was declined. If you think that is a mistake, contact the person who told you about Afterparty.'
              : `Afterparty is invite-only for now, and each request is approved by hand. You are signed in as ${me.data?.user.email ?? 'you'}; come back after you hear back.`}
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            {!denied && (
              <button type="button" className="btn btn-primary" onClick={() => me.refetch()}>
                Check again
              </button>
            )}
            <button type="button" className="btn btn-quiet" onClick={() => signOut()}>
              Sign out
            </button>
          </div>
        </div>
      </main>
    </div>
  )
}
