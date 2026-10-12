import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'
import { AuthProvider, type AppConfig } from './lib/auth'

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, refetchOnWindowFocus: true, retry: 1 } },
})

async function boot() {
  const root = createRoot(document.getElementById('root')!)
  let config: AppConfig
  try {
    const res = await fetch('/api/config')
    config = await res.json()
  } catch {
    root.render(<p style={{ padding: 32 }}>Afterparty could not reach its server. Reload the page to try again.</p>)
    return
  }
  root.render(
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <AuthProvider config={config}>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </AuthProvider>
      </QueryClientProvider>
    </StrictMode>,
  )
}

void boot()
