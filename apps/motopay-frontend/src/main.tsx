import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import { resolveApiBase } from './utils/apiBase'
import './index.css'

try {
  const resolved = resolveApiBase(
    import.meta.env.VITE_API_BASE_URL as string | undefined,
    localStorage.getItem('apiBase')
  )
  localStorage.setItem('apiBase', resolved)
} catch {
  // ignore storage errors (private mode, etc.)
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
