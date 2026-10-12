import { initializeApp, type FirebaseApp } from 'firebase/app'
import {
  GoogleAuthProvider,
  getAuth,
  isSignInWithEmailLink,
  onAuthStateChanged,
  sendSignInLinkToEmail,
  signInWithEmailLink,
  signInWithPopup,
  signOut as fbSignOut,
  type Auth,
  type User,
} from 'firebase/auth'
import { useQueryClient } from '@tanstack/react-query'
import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { setTokenGetter } from './api'

export type AppConfig = {
  firebase: Record<string, string>
  extensionId: string
  /** Every connector build to look for: unpacked (fixed key) and Chrome Web Store. */
  extensionIds?: string[]
  /** Chrome Web Store page for the connector; empty until it is published. */
  connectorStoreUrl?: string
  env: string
}

type AuthState =
  | { status: 'loading' }
  | { status: 'signedOut' }
  | { status: 'signedIn'; email: string; name: string | null; photo: string | null }

type AuthApi = {
  state: AuthState
  config: AppConfig
  google: () => Promise<void>
  emailLink: (email: string) => Promise<void>
  finishEmailLink: (email: string) => Promise<void>
  isEmailLink: () => boolean
  devSignIn: (email: string) => void
  signOut: () => Promise<void>
}

const Ctx = createContext<AuthApi | null>(null)
const DEV_KEY = 'ap.devEmail'
export const EMAIL_KEY = 'ap.emailForSignIn'

function safeGet(key: string) {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}
function safeSet(key: string, value: string | null) {
  try {
    if (value === null) localStorage.removeItem(key)
    else localStorage.setItem(key, value)
  } catch {
    /* storage blocked: sign-in still works for this tab */
  }
}

export function AuthProvider({ config, children }: { config: AppConfig; children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: 'loading' })
  const dev = config.env === 'dev'
  const qc = useQueryClient()
  // Cached data belongs to whoever was signed in: drop it whenever that changes,
  // so the next person on this tab never sees the last one's people.
  const who = useRef<string | null>(null)
  const switchTo = (id: string | null) => {
    if (who.current !== id) qc.clear()
    who.current = id
  }

  const fb = useMemo(() => {
    if (!config.firebase?.apiKey) return null
    const app: FirebaseApp = initializeApp(config.firebase)
    return getAuth(app)
  }, [config])

  useEffect(() => {
    const devEmail = dev ? safeGet(DEV_KEY) : null
    if (devEmail) {
      switchTo(`dev:${devEmail}`)
      setTokenGetter(async () => `Dev ${devEmail}`)
      setState({ status: 'signedIn', email: devEmail, name: null, photo: null })
      return
    }
    if (!fb) {
      setState({ status: 'signedOut' })
      return
    }
    return onAuthStateChanged(fb, (user: User | null) => {
      switchTo(user?.uid ?? null)
      if (user) {
        setTokenGetter(async () => `Bearer ${await user.getIdToken()}`)
        setState({ status: 'signedIn', email: user.email ?? '', name: user.displayName, photo: user.photoURL })
      } else {
        setTokenGetter(null)
        setState({ status: 'signedOut' })
      }
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fb, dev])

  const need = (): Auth => {
    if (!fb) throw new Error('Sign-in is not configured.')
    return fb
  }

  const value: AuthApi = {
    state,
    config,
    google: async () => {
      await signInWithPopup(need(), new GoogleAuthProvider())
    },
    emailLink: async (email) => {
      await sendSignInLinkToEmail(need(), email, {
        url: `${window.location.origin}/signin/finish`,
        handleCodeInApp: true,
      })
      safeSet(EMAIL_KEY, email)
    },
    finishEmailLink: async (email) => {
      await signInWithEmailLink(need(), email, window.location.href)
      safeSet(EMAIL_KEY, null)
    },
    isEmailLink: () => !!fb && isSignInWithEmailLink(fb, window.location.href),
    devSignIn: (email) => {
      switchTo(`dev:${email}`)
      safeSet(DEV_KEY, email)
      setTokenGetter(async () => `Dev ${email}`)
      setState({ status: 'signedIn', email, name: null, photo: null })
    },
    signOut: async () => {
      safeSet(DEV_KEY, null)
      setTokenGetter(null)
      switchTo(null)
      if (fb) await fbSignOut(fb)
      setState({ status: 'signedOut' })
    },
  }
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useAuth() {
  const v = useContext(Ctx)
  if (!v) throw new Error('useAuth outside AuthProvider')
  return v
}

/** Firebase error codes -> what to do about them. */
export function authErrorMessage(err: unknown): string {
  const code = (err as { code?: string })?.code ?? ''
  switch (code) {
    case 'auth/popup-closed-by-user':
    case 'auth/cancelled-popup-request':
      return 'The Google window closed before you finished. Try again.'
    case 'auth/popup-blocked':
      return 'Your browser blocked the Google window. Allow pop-ups for this site, then try again.'
    case 'auth/operation-not-allowed':
      return 'Google sign-in is not turned on yet. Use the email link below.'
    case 'auth/invalid-email':
      return 'That email address is not valid.'
    case 'auth/invalid-action-code':
    case 'auth/expired-action-code':
      return 'This sign-in link expired or was already used. Request a new one.'
    case 'auth/unauthorized-continue-uri':
    case 'auth/unauthorized-domain':
      return 'This address is not allowed to sign in. Open Afterparty from its usual address.'
    default:
      return (err as Error)?.message || 'Sign-in failed. Try again.'
  }
}
