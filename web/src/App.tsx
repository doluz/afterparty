import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom'
import { ErrorNote, PageLoading } from './components/bits'
import { Shell } from './components/Shell'
import { ApiError, useMe } from './lib/api'
import { useAuth } from './lib/auth'
import { EventDetail, Events } from './pages/Events'
import { Home } from './pages/Home'
import { HowItWorks } from './pages/HowItWorks'
import { Landing } from './pages/Landing'
import { Onboarding } from './pages/Onboarding'
import { People } from './pages/People'
import { Privacy } from './pages/Privacy'
import { Settings } from './pages/Settings'
import { FinishSignIn, SignIn } from './pages/SignIn'

/** Signed in and connected: anything else goes to the step it's missing. */
function Gate({ need }: { need: 'signedIn' | 'app' }) {
  const { state, signOut } = useAuth()
  const loc = useLocation()
  const me = useMe(state.status === 'signedIn')

  if (state.status === 'loading') return <PageLoading />
  if (state.status === 'signedOut') return <Navigate to="/signin" replace state={{ from: loc.pathname }} />
  if (me.isLoading) return <PageLoading />
  if (me.error) {
    if (me.error instanceof ApiError && me.error.status === 401) {
      void signOut()
      return <Navigate to="/signin" replace />
    }
    return (
      <div className="mx-auto max-w-md p-8">
        <ErrorNote error={me.error} />
      </div>
    )
  }
  if (need === 'signedIn') return <Outlet />
  const u = me.data!.user
  if (!me.data!.partiful && !u.onboarded_at) return <Navigate to="/onboarding" replace />
  return <Outlet />
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/signin" element={<SignIn />} />
      <Route path="/signin/finish" element={<FinishSignIn />} />
      <Route path="/privacy" element={<Privacy />} />
      <Route path="/how-it-works" element={<HowItWorks />} />
      <Route element={<Gate need="signedIn" />}>
        <Route path="/onboarding" element={<Onboarding />} />
      </Route>
      <Route element={<Gate need="app" />}>
        <Route element={<Shell />}>
          <Route path="/home" element={<Home />} />
          <Route path="/people" element={<People />} />
          <Route path="/events" element={<Events />} />
          <Route path="/events/:id" element={<EventDetail />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
