import { Mail } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { ErrorNote, Spinner, Wordmark } from '../components/bits'
import { EMAIL_KEY, authErrorMessage, useAuth } from '../lib/auth'

function Frame({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col px-5 py-5">
      <Link to="/" className="self-start">
        <Wordmark />
      </Link>
      <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center py-12">
        <div className="glass rise flex flex-col p-7 sm:p-9">{children}</div>
      </main>
    </div>
  )
}

function GoogleMark() {
  return (
    <svg viewBox="0 0 24 24" className="size-[18px]" aria-hidden>
      <path fill="#4285F4" d="M23.5 12.27c0-.85-.08-1.66-.22-2.45H12v4.63h6.46a5.52 5.52 0 0 1-2.4 3.62v3h3.88c2.27-2.09 3.56-5.17 3.56-8.8Z" />
      <path fill="#34A853" d="M12 24c3.24 0 5.96-1.07 7.94-2.9l-3.88-3.02c-1.07.72-2.45 1.15-4.06 1.15-3.12 0-5.77-2.11-6.71-4.95H1.28v3.11A12 12 0 0 0 12 24Z" />
      <path fill="#FBBC05" d="M5.29 14.28a7.2 7.2 0 0 1 0-4.56V6.61H1.28a12 12 0 0 0 0 10.78l4.01-3.11Z" />
      <path fill="#EA4335" d="M12 4.77c1.76 0 3.34.6 4.58 1.8l3.44-3.44A11.5 11.5 0 0 0 12 0 12 12 0 0 0 1.28 6.61l4.01 3.11C6.23 6.88 8.88 4.77 12 4.77Z" />
    </svg>
  )
}

export function SignIn() {
  const auth = useAuth()
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState<string | null>(null)
  const [busy, setBusy] = useState<'google' | 'email' | null>(null)
  const [error, setError] = useState<string | null>(null)

  if (auth.state.status === 'signedIn') return <Navigate to="/home" replace />

  const google = async () => {
    setError(null)
    setBusy('google')
    try {
      await auth.google()
    } catch (e) {
      setError(authErrorMessage(e))
    } finally {
      setBusy(null)
    }
  }
  const sendLink = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setBusy('email')
    try {
      if (auth.config.env === 'dev') {
        auth.devSignIn(email.trim().toLowerCase())
        return
      }
      await auth.emailLink(email.trim())
      setSent(email.trim())
    } catch (e) {
      setError(authErrorMessage(e))
    } finally {
      setBusy(null)
    }
  }

  if (sent) {
    return (
      <Frame>
        <Mail className="size-9 text-uv" aria-hidden />
        <h1 className="mt-5 text-title">Check your inbox</h1>
        <p className="mt-3 text-mute">
          We sent a sign-in link to <span className="text-ink">{sent}</span>. Open it on this device. The link works
          once and expires in an hour.
        </p>
        <button type="button" className="btn btn-quiet mt-8 self-start" onClick={() => setSent(null)}>
          Use a different email
        </button>
      </Frame>
    )
  }

  return (
    <Frame>
      <h1 className="text-title">Sign in</h1>
      <p className="mt-2 text-mute">New here? Signing in creates your account.</p>

      {auth.config.env !== 'dev' && (
        <button type="button" onClick={google} disabled={!!busy} className="btn btn-quiet mt-7 h-12 w-full text-body">
          {busy === 'google' ? <Spinner /> : <GoogleMark />}
          Continue with Google
        </button>
      )}

      <form onSubmit={sendLink} className="mt-6">
        <label htmlFor="email" className="text-caption font-semibold text-mute">
          {auth.config.env === 'dev' ? 'Dev sign-in (local only)' : 'Or get a sign-in link by email'}
        </label>
        <input
          id="email"
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@company.com"
          className="field mt-1.5 h-12"
        />
        <button type="submit" disabled={!!busy || !email} className="btn btn-primary mt-3 h-12 w-full text-body">
          {busy === 'email' ? <Spinner /> : auth.config.env === 'dev' ? 'Sign in' : 'Email me a link'}
        </button>
      </form>
      <div className="mt-4">
        <ErrorNote error={error ? new Error(error) : null} />
      </div>
      <p className="mt-6 text-caption text-faint">
        By signing in you agree to how Afterparty handles data, described in the{' '}
        <Link to="/privacy" className="font-semibold text-mute hover:text-ink">
          privacy page
        </Link>
        .
      </p>
    </Frame>
  )
}

/** Landing page for the emailed link. */
export function FinishSignIn() {
  const auth = useAuth()
  const nav = useNavigate()
  const [email, setEmail] = useState(() => {
    try {
      return localStorage.getItem(EMAIL_KEY) ?? ''
    } catch {
      return ''
    }
  })
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const valid = auth.isEmailLink()

  const finish = async (addr: string) => {
    setBusy(true)
    setError(null)
    try {
      await auth.finishEmailLink(addr)
      nav('/home', { replace: true })
    } catch (e) {
      setError(authErrorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    if (valid && email && auth.state.status === 'signedOut') void finish(email)
    // only on arrival
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [valid, auth.state.status])

  if (auth.state.status === 'signedIn') return <Navigate to="/home" replace />

  return (
    <Frame>
      {!valid ? (
        <>
          <h1 className="text-title">Link not valid</h1>
          <p className="mt-2 text-mute">This sign-in link is broken or incomplete.</p>
          <Link to="/signin" className="btn btn-primary mt-8 self-start">
            Request a new link
          </Link>
        </>
      ) : (
        <>
          <h1 className="text-title">Finish signing in</h1>
          <p className="mt-2 text-mute">Confirm the email address you asked the link for.</p>
          <form
            className="mt-6"
            onSubmit={(e) => {
              e.preventDefault()
              void finish(email)
            }}
          >
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="field h-12" />
            <button type="submit" disabled={busy || !email} className="btn btn-primary mt-3 h-12 w-full text-body">
              {busy ? <Spinner /> : 'Sign in'}
            </button>
          </form>
          <div className="mt-4">
            <ErrorNote error={error ? new Error(error) : null} />
          </div>
        </>
      )}
    </Frame>
  )
}
